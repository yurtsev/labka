from collections.abc import Collection
from uuid import UUID, uuid7

from src.api.courses.dto import (
    CourseDetails,
    CourseFields,
    CoursePreview,
    GroupRef,
    Scale,
    TeacherRef,
)
from src.api.exc.courses import (
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    GroupAlreadyInCourseError,
    GroupNotAvailableError,
    GroupNotInCourseError,
    ScaleLockedError,
    TeacherOnlyError,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.group import GroupSearch
from src.core.db.dto.page import Page, PageRequest
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.course import Course
from src.core.db.models.group import Group
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.security.dto import CurrentUser


class CourseService:
    def __init__(self, uow: UnitOfWork, access: AccessService) -> None:
        self._uow = uow
        self._access = access

    async def list_courses(
        self, user: CurrentUser, archived: bool, page: PageRequest
    ) -> Page[CoursePreview]:
        """Плитки курсов преподавателя или группы студента, новые первыми; архив — отдельно.

        У преподавателя на плитке — сколько попыток ждут проверки.
        """
        if user.role == UserRole.TEACHER:
            courses = await self._uow.courses.page_for_teacher(user.user_id, archived, page)
            pending = await self._uow.submissions.count_pending_by_course(
                [course.id for course in courses.items]
            )
            return courses.map(
                tuple(self._preview(course, pending.get(course.id, 0)) for course in courses.items)
            )
        student = await self._uow.users.get_by_id(user.user_id)
        if student is None or student.group_id is None:
            return Page(items=(), page=page.page, per_page=page.per_page, total=0, pages=1)
        courses = await self._uow.courses.page_for_group(student.group_id, archived, page)
        return courses.map(tuple(self._preview(course, None) for course in courses.items))

    async def get_course(self, user: CurrentUser, course_id: UUID) -> CourseDetails:
        """Курс, который пользователь может смотреть; архивный тоже.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
        """
        return self._details(await self._readable(user, course_id))

    async def list_available_groups(
        self, user: CurrentUser, search: GroupSearch, page: PageRequest
    ) -> Page[GroupRef]:
        """Группы, которые преподаватель может добавить в курс, с поиском по названию.

        Raises:
            TeacherOnlyError: пользователь не преподаватель.
        """
        self._require_teacher(user)
        groups = await self._uow.groups.page_attached_to_teacher(user.user_id, search, page)
        return groups.map(tuple(GroupRef(id=group.id, name=group.name) for group in groups.items))

    async def create_course(
        self, user: CurrentUser, fields: CourseFields, group_ids: Collection[UUID]
    ) -> CourseDetails:
        """Создаёт курс для прикреплённых к преподавателю групп.

        Raises:
            TeacherOnlyError: пользователь не преподаватель.
            GroupNotAvailableError: группа не прикреплена к преподавателю или неактивна.
        """
        self._require_teacher(user)
        groups = await self._attachable_groups(user.user_id, group_ids)
        course = Course(id=uuid7(), teacher_id=user.user_id, groups=groups)
        self._apply_fields(course, fields)
        self._uow.courses.add(course)
        await self._uow.commit()
        return await self._reload(course.id)

    async def update_course(
        self, user: CurrentUser, course_id: UUID, fields: CourseFields
    ) -> CourseDetails:
        """Меняет название, описание, шкалу по умолчанию и пояснение к оценке.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ScaleLockedError: шкала меняется, а по заданиям со шкалой курса уже есть попытки.
        """
        course = await self._editable(user, course_id)
        scale = fields.scale
        if (scale.type, scale.min, scale.max) != (
            course.scale_type,
            course.scale_min,
            course.scale_max,
        ) and await self._uow.assignments.inherits_scale_with_submissions(course.id):
            raise ScaleLockedError({"course_id": str(course.id)})
        self._apply_fields(course, fields)
        await self._uow.commit()
        return await self._reload(course.id)

    async def add_group(self, user: CurrentUser, course_id: UUID, group_id: UUID) -> CourseDetails:
        """Добавляет в курс прикреплённую к преподавателю группу: она сразу видит курс.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            GroupAlreadyInCourseError: группа уже в курсе.
            GroupNotAvailableError: группа не прикреплена к преподавателю или неактивна.
        """
        course = await self._editable(user, course_id)
        if any(group.id == group_id for group in course.groups):
            raise GroupAlreadyInCourseError({"group_id": str(group_id)})
        course.groups.extend(await self._attachable_groups(user.user_id, [group_id]))
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            # Параллельный запрос добавил ту же группу: проверка выше его не видит.
            if exc.constraint == "pk_course_groups":
                raise GroupAlreadyInCourseError({"group_id": str(group_id)}) from exc
            raise
        return await self._reload(course.id)

    async def remove_group(
        self, user: CurrentUser, course_id: UUID, group_id: UUID
    ) -> CourseDetails:
        """Убирает группу из курса: её студенты перестают видеть курс, попытки остаются.
        Без групп курс остаётся у преподавателя.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            GroupNotInCourseError: группы нет в курсе.
        """
        course = await self._editable(user, course_id)
        remaining = [group for group in course.groups if group.id != group_id]
        if len(remaining) == len(course.groups):
            raise GroupNotInCourseError({"group_id": str(group_id)})
        course.groups = remaining
        await self._uow.commit()
        return await self._reload(course.id)

    async def set_archived(
        self, user: CurrentUser, course_id: UUID, archived: bool
    ) -> CourseDetails:
        """Отправляет курс в архив или возвращает из него.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
        """
        course = await self._owned(user, course_id)
        course.is_archived = archived
        await self._uow.commit()
        return await self._reload(course.id)

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

    async def _owned(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.owned_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

    async def _editable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.editable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc
        except access_exc.CourseArchivedError as exc:
            raise CourseArchivedError({"course_id": str(course_id)}) from exc

    async def _attachable_groups(
        self, teacher_id: UUID, group_ids: Collection[UUID]
    ) -> list[Group]:
        try:
            return await self._access.attachable_groups(teacher_id, group_ids)
        except access_exc.GroupNotAttachedError as exc:
            raise GroupNotAvailableError(exc.context) from exc

    async def _reload(self, course_id: UUID) -> CourseDetails:
        course = await self._uow.courses.get_with_details(course_id)
        if course is None:
            raise InternalError({"course_id": str(course_id)})
        return self._details(course)

    @staticmethod
    def _require_teacher(user: CurrentUser) -> None:
        if user.role != UserRole.TEACHER:
            raise TeacherOnlyError

    @staticmethod
    def _apply_fields(course: Course, fields: CourseFields) -> None:
        course.name = fields.name
        course.description = fields.description
        course.scale_type = fields.scale.type
        course.scale_min = fields.scale.min
        course.scale_max = fields.scale.max
        course.grading_note = fields.grading_note

    @staticmethod
    def _preview(course: Course, pending_reviews: int | None) -> CoursePreview:
        return CoursePreview(
            id=course.id,
            name=course.name,
            teacher=CourseService._teacher(course),
            is_archived=course.is_archived,
            groups=CourseService._groups(course),
            pending_reviews=pending_reviews,
        )

    @staticmethod
    def _details(course: Course) -> CourseDetails:
        return CourseDetails(
            id=course.id,
            name=course.name,
            description=course.description,
            teacher=CourseService._teacher(course),
            scale=Scale(type=course.scale_type, min=course.scale_min, max=course.scale_max),
            grading_note=course.grading_note,
            is_archived=course.is_archived,
            groups=CourseService._groups(course),
        )

    @staticmethod
    def _teacher(course: Course) -> TeacherRef:
        teacher = course.teacher
        return TeacherRef(
            id=teacher.id,
            last_name=teacher.last_name,
            first_name=teacher.first_name,
            middle_name=teacher.middle_name,
        )

    @staticmethod
    def _groups(course: Course) -> tuple[GroupRef, ...]:
        return tuple(GroupRef(id=group.id, name=group.name) for group in course.groups)
