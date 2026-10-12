from uuid import UUID, uuid7

from src.api.exams.dto import Exam, ExamFields, GroupRef
from src.api.exc.exams import (
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    DateOutsideSemesterError,
    ExamAlreadyExistsError,
    ExamNotFoundError,
    GroupNotInCourseError,
    ResultsExistError,
    SlotNotFoundError,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.course import Course
from src.core.db.models.course_exam import CourseExam
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.schedule import exc as schedule_exc
from src.core.schedule.dto import Slot
from src.core.schedule.service import ScheduleService
from src.core.security.dto import CurrentUser


class ExamService:
    """Зачёты и экзамены курса: у группы в курсе один, дата в семестре, время — окно пары.
    Назначает преподаватель, студент видит экзамен своей группы."""

    def __init__(self, uow: UnitOfWork, access: AccessService) -> None:
        self._uow = uow
        self._access = access

    async def list_exams(self, user: CurrentUser, course_id: UUID) -> tuple[Exam, ...]:
        """Экзамены курса по дате; студенту — только его группы.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
        """
        course = await self._readable(user, course_id)
        group_id = None
        if user.role == UserRole.STUDENT:
            student = await self._uow.users.get_by_id(user.user_id)
            group_id = student.group_id if student is not None else None
        exams = await self._uow.course_exams.list_for_course(course.id, group_id)
        return tuple(self._dto(exam) for exam in exams)

    async def create(self, user: CurrentUser, course_id: UUID, fields: ExamFields) -> Exam:
        """Назначает группе зачёт или экзамен.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            GroupNotInCourseError: группы нет в курсе.
            ExamAlreadyExistsError: у группы в курсе уже есть экзамен.
            SlotNotFoundError: в сетке нет такой пары.
            DateOutsideSemesterError: дата вне семестра курса.
        """
        course = await self._editable(user, course_id)
        slot = await self._checked(course, fields)
        if await self._uow.course_exams.get_for_group(course.id, fields.group_id) is not None:
            raise ExamAlreadyExistsError({"group_id": str(fields.group_id)})
        exam = CourseExam(id=uuid7(), course_id=course.id)
        self._apply(exam, fields, slot)
        self._uow.course_exams.add(exam)
        await self._commit(fields.group_id)
        return await self._reload(course.id, exam.id)

    async def update(
        self, user: CurrentUser, course_id: UUID, exam_id: UUID, fields: ExamFields
    ) -> Exam:
        """Меняет экзамен.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ExamNotFoundError: экзамена нет в этом курсе.
            GroupNotInCourseError: группы нет в курсе.
            ExamAlreadyExistsError: у новой группы в курсе уже есть экзамен.
            ResultsExistError: смена формы или группы, когда результаты уже выставлены.
            SlotNotFoundError: в сетке нет такой пары.
            DateOutsideSemesterError: дата вне семестра курса.
        """
        course = await self._editable(user, course_id)
        exam = await self._uow.course_exams.get_in_course(course.id, exam_id)
        if exam is None:
            raise ExamNotFoundError({"exam_id": str(exam_id)})
        slot = await self._checked(course, fields)
        if (
            fields.group_id != exam.group_id
            and await self._uow.course_exams.get_for_group(course.id, fields.group_id) is not None
        ):
            raise ExamAlreadyExistsError({"group_id": str(fields.group_id)})
        if (fields.group_id, fields.exam_type) != (
            exam.group_id,
            exam.exam_type,
        ) and await self._uow.final_grades.exists_for_group(course.id, exam.group_id):
            raise ResultsExistError({"group_id": str(exam.group_id)})
        self._apply(exam, fields, slot)
        await self._commit(fields.group_id)
        return await self._reload(course.id, exam.id)

    async def delete(self, user: CurrentUser, course_id: UUID, exam_id: UUID) -> None:
        """Удаляет экзамен.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ExamNotFoundError: экзамена нет в этом курсе.
            ResultsExistError: по экзамену уже выставлены результаты.
        """
        course = await self._editable(user, course_id)
        exam = await self._uow.course_exams.get_in_course(course.id, exam_id)
        if exam is None:
            raise ExamNotFoundError({"exam_id": str(exam_id)})
        if await self._uow.final_grades.exists_for_group(course.id, exam.group_id):
            raise ResultsExistError({"group_id": str(exam.group_id)})
        await self._uow.course_exams.delete(exam)
        await self._uow.commit()

    async def _checked(self, course: Course, fields: ExamFields) -> Slot:
        if not await self._uow.courses.has_group(course.id, fields.group_id):
            raise GroupNotInCourseError({"group_id": str(fields.group_id)})
        try:
            slot = ScheduleService.slot(fields.slot)
        except schedule_exc.SlotNotFoundError as exc:
            raise SlotNotFoundError(exc.context) from exc
        semester = ScheduleService.semester(course.term, course.year)
        if not semester.starts_on <= fields.day <= semester.ends_on:
            raise DateOutsideSemesterError(
                {
                    "starts_on": semester.starts_on.isoformat(),
                    "ends_on": semester.ends_on.isoformat(),
                }
            )
        return slot

    async def _commit(self, group_id: UUID) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            await self._uow.rollback()
            # Параллельный запрос назначил экзамен той же группе: проверка выше его не видит.
            if exc.constraint == "uq_course_exams_course_id_group_id":
                raise ExamAlreadyExistsError({"group_id": str(group_id)}) from exc
            raise

    async def _reload(self, course_id: UUID, exam_id: UUID) -> Exam:
        exam = await self._uow.course_exams.get_in_course(course_id, exam_id)
        if exam is None:
            raise InternalError({"exam_id": str(exam_id)})
        return self._dto(exam)

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
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

    @staticmethod
    def _apply(exam: CourseExam, fields: ExamFields, slot: Slot) -> None:
        exam.group_id = fields.group_id
        exam.exam_type = fields.exam_type
        exam.day = fields.day
        exam.starts_at = slot.starts_at
        exam.ends_at = slot.ends_at
        exam.room = fields.room

    @staticmethod
    def _dto(exam: CourseExam) -> Exam:
        return Exam(
            id=exam.id,
            group=GroupRef(id=exam.group.id, name=exam.group.name),
            exam_type=exam.exam_type,
            day=exam.day,
            slot=ScheduleService.slot_number(exam.starts_at, exam.ends_at),
            starts_at=exam.starts_at,
            ends_at=exam.ends_at,
            room=exam.room,
        )
