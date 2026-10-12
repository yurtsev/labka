from datetime import date, timedelta
from uuid import UUID

from src.api.calendar.dto import Calendar, CourseRef, GroupRef
from src.api.calendar.presenter import CalendarPresenter
from src.core.db.enums import UserRole
from src.core.db.models.course_exam import CourseExam
from src.core.db.models.extra_lesson import ExtraLesson
from src.core.db.models.personal_task import PersonalTask
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
        tasks: list[PersonalTask] = []
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
            statuses = {
                assignment.id: GradingService.progress(
                    progress.get((assignment.id, user.user_id))
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
