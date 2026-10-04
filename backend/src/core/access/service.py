from collections.abc import Collection
from uuid import UUID

from src.core.access.exc import (
    CourseAccessDeniedError,
    CourseArchivedError,
    CourseNotFoundError,
    GroupNotAttachedError,
)
from src.core.db.enums import UserRole
from src.core.db.models.course import Course
from src.core.db.models.group import Group
from src.core.db.uow import UnitOfWork
from src.core.security.dto import CurrentUser


class AccessService:
    """Проверки принадлежности: чей курс, чья группа, можно ли курс менять."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def readable_course(self, user: CurrentUser, course_id: UUID) -> Course:
        """Курс, который пользователь может смотреть: свой у преподавателя, курс своей
        группы у студента. Архивный курс тоже читается.

        Returns:
            Курс с загруженными преподавателем и группами.

        Raises:
            CourseNotFoundError: курса нет.
            CourseAccessDeniedError: курс чужой.
        """
        course = await self._get_course(course_id)
        if user.role == UserRole.TEACHER and course.teacher_id == user.user_id:
            return course
        if user.role == UserRole.STUDENT:
            student = await self._uow.users.get_by_id(user.user_id)
            if (
                student is not None
                and student.group_id is not None
                and await self._uow.courses.has_group(course.id, student.group_id)
            ):
                return course
        raise CourseAccessDeniedError({"course_id": str(course_id)})

    async def owned_course(self, user: CurrentUser, course_id: UUID) -> Course:
        """Свой курс преподавателя, в том числе архивный.

        Raises:
            CourseNotFoundError: курса нет.
            CourseAccessDeniedError: курс чужой или пользователь не преподаватель.
        """
        course = await self._get_course(course_id)
        if user.role != UserRole.TEACHER or course.teacher_id != user.user_id:
            raise CourseAccessDeniedError({"course_id": str(course_id)})
        return course

    async def editable_course(self, user: CurrentUser, course_id: UUID) -> Course:
        """Свой курс преподавателя, который можно менять: не архивный.

        Raises:
            CourseNotFoundError: курса нет.
            CourseAccessDeniedError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве — только для чтения.
        """
        course = await self.owned_course(user, course_id)
        if course.is_archived:
            raise CourseArchivedError({"course_id": str(course_id)})
        return course

    async def attachable_groups(self, teacher_id: UUID, group_ids: Collection[UUID]) -> list[Group]:
        """Группы, которые преподаватель может добавить в курс.

        Raises:
            GroupNotAttachedError: хотя бы одна группа не прикреплена к преподавателю
                или неактивна.
        """
        groups = await self._uow.groups.list_attached_to_teacher(teacher_id, group_ids)
        missing = set(group_ids) - {group.id for group in groups}
        if missing:
            raise GroupNotAttachedError({"group_ids": sorted(str(item) for item in missing)})
        return groups

    async def _get_course(self, course_id: UUID) -> Course:
        course = await self._uow.courses.get_with_details(course_id)
        if course is None:
            raise CourseNotFoundError({"course_id": str(course_id)})
        return course
