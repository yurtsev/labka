from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid7

from src.api.calendar.dto import Calendar, CourseRef, GroupRef, PersonalTask, TaskFields
from src.api.calendar.presenter import CalendarPresenter
from src.api.exc.calendar import InvalidRangeError, StudentOnlyError, TaskNotFoundError
from src.config import cfg
from src.core.db.enums import UserRole
from src.core.db.models.course_exam import CourseExam
from src.core.db.models.extra_lesson import ExtraLesson
from src.core.db.models.personal_task import PersonalTask as PersonalTaskModel
from src.core.db.models.schedule_rule import ScheduleRule
from src.core.db.uow import UnitOfWork
from src.core.grading.service import GradingService
from src.core.schedule.enums import CalendarView
from src.core.schedule.service import ScheduleService
from src.core.security.dto import CurrentUser
from src.core.utils.moscow_time import start_of_day_moscow


class CalendarService:
    """Календарь: занятия, дедлайны заданий и (у студента) личные задачи за период.

    Архивные курсы в календаре не показываются.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get(self, user: CurrentUser, view: CalendarView, day: date) -> Calendar:
        """Календарь на день, неделю или месяц, в который попадает дата."""
        period = ScheduleService.period(view, day)
        first, last = period.starts_on, period.ends_on
        is_student = user.role == UserRole.STUDENT
        rules: list[ScheduleRule] = []
        extras: list[ExtraLesson] = []
        exams: list[CourseExam] = []
        tasks: list[PersonalTaskModel] = []
        group_id: UUID | None = None
        if is_student:
            student = await self._uow.users.get_by_id(user.user_id)
            group_id = student.group_id if student is not None else None
            if group_id is not None:
                rules = await self._uow.schedule_rules.list_for_group(group_id)
                extras = await self._uow.extra_lessons.list_for_group(group_id, first, last)
                exams = await self._uow.course_exams.list_for_group(group_id, first, last)
            tasks = await self._uow.personal_tasks.list_between(user.user_id, first, last)
        else:
            rules = await self._uow.schedule_rules.list_for_teacher(user.user_id)
            extras = await self._uow.extra_lessons.list_for_teacher(user.user_id, first, last)
            exams = await self._uow.course_exams.list_for_teacher(user.user_id, first, last)
        assignments = await self._uow.assignments.list_with_deadline(
            None if is_student else user.user_id,
            group_id if is_student else None,
            start_of_day_moscow(first),
            start_of_day_moscow(last + timedelta(days=1)),
        )
        statuses = None
        if is_student:
            progress = await self._uow.submissions.progress(
                [assignment.id for assignment in assignments], [user.user_id]
            )
            now = datetime.now(UTC)
            statuses = {
                assignment.id: GradingService.progress(
                    progress.get((assignment.id, user.user_id)), assignment, now
                ).status
                for assignment in assignments
            }
        occurrences = ScheduleService.occurrences(
            [ScheduleService.to_rule(rule) for rule in rules],
            [ScheduleService.to_extra(extra) for extra in extras],
            first,
            last,
        )
        sources: list[ScheduleRule | ExtraLesson | CourseExam] = [*rules, *extras, *exams]
        courses = {item.course.id: CourseRef(item.course.id, item.course.name) for item in sources}
        groups = {item.group.id: GroupRef(item.group.id, item.group.name) for item in sources}
        return Calendar(
            period=period,
            weeks=tuple(ScheduleService.weeks(first, last)),
            items=CalendarPresenter.items(
                occurrences, courses, groups, exams, assignments, statuses, tasks
            ),
        )


class PersonalTaskService:
    """Личные задачи студента: видит и ведёт только он сам."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_between(
        self, user: CurrentUser, first: date, last: date
    ) -> tuple[PersonalTask, ...]:
        """Задачи за период по дате и времени; задачи без времени — первыми в своём дне.

        Raises:
            StudentOnlyError: пользователь не студент.
            InvalidRangeError: начало позже конца или период длиннее допустимого.
        """
        self._require_student(user)
        if last < first or (last - first).days + 1 > cfg.schedule.personal_tasks_max_range_days:
            raise InvalidRangeError({"max_days": cfg.schedule.personal_tasks_max_range_days})
        tasks = await self._uow.personal_tasks.list_between(user.user_id, first, last)
        return tuple(self._dto(task) for task in tasks)

    async def create(self, user: CurrentUser, fields: TaskFields) -> PersonalTask:
        """Создаёт задачу.

        Raises:
            StudentOnlyError: пользователь не студент.
        """
        self._require_student(user)
        task = PersonalTaskModel(
            id=uuid7(),
            student_id=user.user_id,
            title=fields.title,
            due_date=fields.due_date,
            due_time=fields.due_time,
        )
        self._uow.personal_tasks.add(task)
        await self._uow.commit()
        return await self._reload(user, task.id)

    async def update(self, user: CurrentUser, task_id: UUID, fields: TaskFields) -> PersonalTask:
        """Меняет название, дату и время задачи.

        Raises:
            StudentOnlyError: пользователь не студент.
            TaskNotFoundError: задачи нет или она чужая.
        """
        task = await self._own(user, task_id)
        task.title = fields.title
        task.due_date = fields.due_date
        task.due_time = fields.due_time
        await self._uow.commit()
        return await self._reload(user, task.id)

    async def set_done(self, user: CurrentUser, task_id: UUID, is_done: bool) -> PersonalTask:
        """Отмечает задачу сделанной или возвращает в работу.

        Raises:
            StudentOnlyError: пользователь не студент.
            TaskNotFoundError: задачи нет или она чужая.
        """
        task = await self._own(user, task_id)
        task.is_done = is_done
        await self._uow.commit()
        return await self._reload(user, task.id)

    async def delete(self, user: CurrentUser, task_id: UUID) -> None:
        """Удаляет задачу.

        Raises:
            StudentOnlyError: пользователь не студент.
            TaskNotFoundError: задачи нет или она чужая.
        """
        task = await self._own(user, task_id)
        await self._uow.personal_tasks.delete(task)
        await self._uow.commit()

    async def _own(self, user: CurrentUser, task_id: UUID) -> PersonalTaskModel:
        self._require_student(user)
        task = await self._uow.personal_tasks.get_own(user.user_id, task_id)
        if task is None:
            raise TaskNotFoundError({"task_id": str(task_id)})
        return task

    async def _reload(self, user: CurrentUser, task_id: UUID) -> PersonalTask:
        return self._dto(await self._own(user, task_id))

    @staticmethod
    def _require_student(user: CurrentUser) -> None:
        if user.role != UserRole.STUDENT:
            raise StudentOnlyError

    @staticmethod
    def _dto(task: PersonalTaskModel) -> PersonalTask:
        return PersonalTask(
            id=task.id,
            title=task.title,
            due_date=task.due_date,
            due_time=task.due_time,
            is_done=task.is_done,
            created_at=task.created_at,
        )
