from datetime import date, datetime, timedelta

from src.api.home.dto import (
    CourseRef,
    GroupRef,
    Home,
    HomeCourse,
    HomeDeadline,
    HomeLesson,
    TeacherRef,
)
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.db.enums import UserRole
from src.core.db.models.assignment import Assignment
from src.core.db.models.course import Course
from src.core.db.models.extra_lesson import ExtraLesson
from src.core.db.models.schedule_rule import ScheduleRule
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.grading.enums import ProgressStatus
from src.core.grading.service import GradingService
from src.core.schedule.service import ScheduleService
from src.core.security.dto import CurrentUser
from src.core.utils.moscow_time import now_moscow


class HomeService:
    """Главная: что делать дальше. Неархивные курсы; архив отдельно, через список курсов."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get(self, user: CurrentUser) -> Home:
        """Сводка главной для студента или преподавателя."""
        if user.role == UserRole.STUDENT:
            return await self._student(user)
        return await self._teacher(user)

    async def _student(self, user: CurrentUser) -> Home:
        student = await self._uow.users.get_by_id(user.user_id)
        group_id = student.group_id if student is not None else None
        if group_id is None:
            return Home(None, (), None, (), (), 0)
        now = now_moscow()
        limit = cfg.dashboard.upcoming_deadlines + 1
        assignments = await self._uow.submissions.list_pending_deadlines(
            user.user_id, group_id, now, limit
        )
        progress = await self._uow.submissions.progress(
            [assignment.id for assignment in assignments], [user.user_id]
        )
        deadlines = tuple(
            self._deadline(
                assignment,
                GradingService.progress(progress.get((assignment.id, user.user_id))).status,
            )
            for assignment in assignments
        )
        courses = await self._uow.courses.page_for_group(
            group_id, False, PageRequest(1, cfg.dashboard.courses)
        )
        unsubmitted = await self._uow.assignments.count_unsubmitted_by_course(
            user.user_id, [course.id for course in courses.items]
        )
        rules = await self._uow.schedule_rules.list_for_group(group_id)
        extras = await self._uow.extra_lessons.list_for_group(group_id, *self._horizon(now.date()))
        return Home(
            nearest_deadline=deadlines[0] if deadlines else None,
            upcoming_deadlines=deadlines[1:],
            pending_reviews=None,
            upcoming_lessons=self._lessons(rules, extras, now),
            courses=tuple(
                self._course(course, not_submitted=unsubmitted.get(course.id, 0))
                for course in courses.items
            ),
            courses_total=courses.total,
        )

    async def _teacher(self, user: CurrentUser) -> Home:
        now = now_moscow()
        courses = await self._uow.courses.page_for_teacher(
            user.user_id, False, PageRequest(1, cfg.dashboard.courses)
        )
        pending = await self._uow.submissions.count_pending_by_course(
            [course.id for course in courses.items]
        )
        rules = await self._uow.schedule_rules.list_for_teacher(user.user_id)
        extras = await self._uow.extra_lessons.list_for_teacher(
            user.user_id, *self._horizon(now.date())
        )
        return Home(
            nearest_deadline=None,
            upcoming_deadlines=(),
            pending_reviews=await self._uow.submissions.count_pending_for_teacher(user.user_id),
            upcoming_lessons=self._lessons(rules, extras, now),
            courses=tuple(
                self._course(course, pending_reviews=pending.get(course.id, 0))
                for course in courses.items
            ),
            courses_total=courses.total,
        )

    @staticmethod
    def _horizon(today: date) -> tuple[date, date]:
        return today, today + timedelta(days=cfg.dashboard.lessons_horizon_days)

    @staticmethod
    def _lessons(
        rules: list[ScheduleRule], extras: list[ExtraLesson], now: datetime
    ) -> tuple[HomeLesson, ...]:
        """Ближайшие занятия, считая сегодняшние, которые ещё не закончились."""
        first, last = HomeService._horizon(now.date())
        sources: list[ScheduleRule | ExtraLesson] = [*rules, *extras]
        courses = {item.course.id: CourseRef(item.course.id, item.course.name) for item in sources}
        groups = {item.group.id: GroupRef(item.group.id, item.group.name) for item in sources}
        occurrences = ScheduleService.occurrences(
            [ScheduleService.to_rule(rule) for rule in rules],
            [ScheduleService.to_extra(extra) for extra in extras],
            first,
            last,
        )
        upcoming = [item for item in occurrences if item.day > first or item.ends_at > now.time()]
        return tuple(
            HomeLesson(
                day=item.day,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                slot=ScheduleService.slot_number(item.starts_at, item.ends_at),
                lesson_type=item.lesson_type,
                room=item.room,
                is_extra=item.is_extra,
                course=courses[item.course_id],
                group=groups[item.group_id],
            )
            for item in upcoming[: cfg.dashboard.upcoming_lessons]
        )

    @staticmethod
    def _deadline(assignment: Assignment, status: ProgressStatus) -> HomeDeadline:
        course = assignment.course
        if assignment.deadline_at is None:
            raise InternalError({"assignment_id": str(assignment.id)})
        return HomeDeadline(
            assignment_id=assignment.id,
            title=assignment.title,
            type=assignment.type,
            deadline_type=assignment.deadline_type,
            deadline_at=assignment.deadline_at,
            course=CourseRef(course.id, course.name),
            teacher=HomeService._teacher_ref(course),
            status=status,
        )

    @staticmethod
    def _course(
        course: Course, *, not_submitted: int | None = None, pending_reviews: int | None = None
    ) -> HomeCourse:
        return HomeCourse(
            id=course.id,
            name=course.name,
            teacher=HomeService._teacher_ref(course),
            groups=tuple(GroupRef(group.id, group.name) for group in course.groups),
            not_submitted=not_submitted,
            pending_reviews=pending_reviews,
        )

    @staticmethod
    def _teacher_ref(course: Course) -> TeacherRef:
        teacher = course.teacher
        return TeacherRef(
            id=teacher.id,
            last_name=teacher.last_name,
            first_name=teacher.first_name,
            middle_name=teacher.middle_name,
        )
