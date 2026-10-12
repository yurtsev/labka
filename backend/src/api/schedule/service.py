from uuid import UUID, uuid7

from src.api.exc.schedule import (
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    DateOutsideClassesError,
    ExtraLessonNotFoundError,
    GroupNotInCourseError,
    RuleNotFoundError,
    SlotNotFoundError,
)
from src.api.schedule.dto import (
    CourseSchedule,
    Extra,
    ExtraFields,
    GroupRef,
    Rule,
    RuleFields,
    Slots,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.enums import NotificationType, UserRole
from src.core.db.models.course import Course
from src.core.db.models.extra_lesson import ExtraLesson
from src.core.db.models.group import Group
from src.core.db.models.schedule_rule import ScheduleRule
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.notifications.dto import Payload
from src.core.notifications.service import NotificationService
from src.core.schedule import exc as schedule_exc
from src.core.schedule.dto import Slot
from src.core.schedule.service import ScheduleService
from src.core.security.dto import CurrentUser


class ScheduleCourseService:
    """Расписание курса: правила с повтором и разовые занятия, только в окнах пар и в
    пределах семестра курса. Правит преподаватель, студент видит свою группу."""

    def __init__(
        self, uow: UnitOfWork, access: AccessService, notifications: NotificationService
    ) -> None:
        self._uow = uow
        self._access = access
        self._notifications = notifications

    @staticmethod
    def slots() -> Slots:
        """Сетка пар: занятия ставятся только на эти окна."""
        return Slots(items=ScheduleService.slots())

    async def get(self, user: CurrentUser, course_id: UUID) -> CourseSchedule:
        """Расписание курса; студенту — только правила и занятия его группы.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
        """
        course = await self._readable(user, course_id)
        group_id = None
        if user.role == UserRole.STUDENT:
            student = await self._uow.users.get_by_id(user.user_id)
            group_id = student.group_id if student is not None else None
        rules = await self._uow.schedule_rules.list_for_course(course.id, group_id)
        extras = await self._uow.extra_lessons.list_for_course(course.id, group_id)
        return CourseSchedule(
            semester=ScheduleService.semester(course.term, course.year),
            rules=tuple(self._rule(rule) for rule in rules),
            extras=tuple(self._extra(extra) for extra in extras),
        )

    async def create_rule(self, user: CurrentUser, course_id: UUID, fields: RuleFields) -> Rule:
        """Добавляет правило расписания: занятия сразу появляются в календаре.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            GroupNotInCourseError: группы нет в курсе.
            SlotNotFoundError: в сетке нет такой пары.
        """
        course = await self._editable(user, course_id)
        await self._check_group(course, fields.group_id)
        slot = self._slot(fields.slot)
        rule = ScheduleRule(id=uuid7(), course_id=course.id)
        self._apply_rule(rule, fields, slot)
        self._uow.schedule_rules.add(rule)
        await self._notify_changed(course, fields.group_id)
        await self._uow.commit()
        return await self._reload_rule(course.id, rule.id)

    async def update_rule(
        self, user: CurrentUser, course_id: UUID, rule_id: UUID, fields: RuleFields
    ) -> Rule:
        """Меняет правило расписания.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            RuleNotFoundError: правила нет в этом курсе.
            GroupNotInCourseError: группы нет в курсе.
            SlotNotFoundError: в сетке нет такой пары.
        """
        course = await self._editable(user, course_id)
        rule = await self._uow.schedule_rules.get_in_course(course.id, rule_id)
        if rule is None:
            raise RuleNotFoundError({"rule_id": str(rule_id)})
        await self._check_group(course, fields.group_id)
        previous_group_id = rule.group_id
        self._apply_rule(rule, fields, self._slot(fields.slot))
        await self._notify_changed(course, fields.group_id, previous_group_id)
        await self._uow.commit()
        return await self._reload_rule(course.id, rule.id)

    async def delete_rule(self, user: CurrentUser, course_id: UUID, rule_id: UUID) -> None:
        """Удаляет правило расписания.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            RuleNotFoundError: правила нет в этом курсе.
        """
        course = await self._editable(user, course_id)
        rule = await self._uow.schedule_rules.get_in_course(course.id, rule_id)
        if rule is None:
            raise RuleNotFoundError({"rule_id": str(rule_id)})
        await self._uow.schedule_rules.delete(rule)
        await self._notify_changed(course, rule.group_id)
        await self._uow.commit()

    async def create_extra(self, user: CurrentUser, course_id: UUID, fields: ExtraFields) -> Extra:
        """Добавляет разовое занятие на дату в пределах семестра, пока идут пары.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            GroupNotInCourseError: группы нет в курсе.
            SlotNotFoundError: в сетке нет такой пары.
            DateOutsideClassesError: дата вне семестра или после конца пар.
        """
        course = await self._editable(user, course_id)
        await self._check_group(course, fields.group_id)
        slot = self._slot(fields.slot)
        self._check_day(course, fields)
        extra = ExtraLesson(id=uuid7(), course_id=course.id)
        self._apply_extra(extra, fields, slot)
        self._uow.extra_lessons.add(extra)
        await self._notify_changed(course, fields.group_id)
        await self._uow.commit()
        return await self._reload_extra(course.id, extra.id)

    async def update_extra(
        self, user: CurrentUser, course_id: UUID, extra_id: UUID, fields: ExtraFields
    ) -> Extra:
        """Меняет разовое занятие.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ExtraLessonNotFoundError: занятия нет в этом курсе.
            GroupNotInCourseError: группы нет в курсе.
            SlotNotFoundError: в сетке нет такой пары.
            DateOutsideClassesError: дата вне семестра или после конца пар.
        """
        course = await self._editable(user, course_id)
        extra = await self._uow.extra_lessons.get_in_course(course.id, extra_id)
        if extra is None:
            raise ExtraLessonNotFoundError({"extra_lesson_id": str(extra_id)})
        await self._check_group(course, fields.group_id)
        slot = self._slot(fields.slot)
        self._check_day(course, fields)
        previous_group_id = extra.group_id
        self._apply_extra(extra, fields, slot)
        await self._notify_changed(course, fields.group_id, previous_group_id)
        await self._uow.commit()
        return await self._reload_extra(course.id, extra.id)

    async def delete_extra(self, user: CurrentUser, course_id: UUID, extra_id: UUID) -> None:
        """Удаляет разовое занятие.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ExtraLessonNotFoundError: занятия нет в этом курсе.
        """
        course = await self._editable(user, course_id)
        extra = await self._uow.extra_lessons.get_in_course(course.id, extra_id)
        if extra is None:
            raise ExtraLessonNotFoundError({"extra_lesson_id": str(extra_id)})
        await self._uow.extra_lessons.delete(extra)
        await self._notify_changed(course, extra.group_id)
        await self._uow.commit()

    async def _notify_changed(
        self, course: Course, group_id: UUID, previous_group_id: UUID | None = None
    ) -> None:
        """Сообщает студентам группы (и прежней, если занятие перенесли), что расписание
        изменилось; серия правок — одно непрочитанное уведомление."""
        for affected in dict.fromkeys([group_id, previous_group_id]):
            if affected is not None:
                await self._notifications.notify_group(
                    affected,
                    NotificationType.SCHEDULE_CHANGED,
                    Payload(course_id=course.id, course_name=course.name),
                    dedup_key=f"schedule:{course.id}",
                )

    async def _check_group(self, course: Course, group_id: UUID) -> None:
        if not await self._uow.courses.has_group(course.id, group_id):
            raise GroupNotInCourseError({"group_id": str(group_id)})

    @staticmethod
    def _slot(number: int) -> Slot:
        try:
            return ScheduleService.slot(number)
        except schedule_exc.SlotNotFoundError as exc:
            raise SlotNotFoundError(exc.context) from exc

    @staticmethod
    def _check_day(course: Course, fields: ExtraFields) -> None:
        semester = ScheduleService.semester(course.term, course.year)
        if not semester.starts_on <= fields.day <= semester.classes_end_on:
            raise DateOutsideClassesError(
                {
                    "starts_on": semester.starts_on.isoformat(),
                    "classes_end_on": semester.classes_end_on.isoformat(),
                }
            )

    async def _reload_rule(self, course_id: UUID, rule_id: UUID) -> Rule:
        rule = await self._uow.schedule_rules.get_in_course(course_id, rule_id)
        if rule is None:
            raise InternalError({"rule_id": str(rule_id)})
        return self._rule(rule)

    async def _reload_extra(self, course_id: UUID, extra_id: UUID) -> Extra:
        extra = await self._uow.extra_lessons.get_in_course(course_id, extra_id)
        if extra is None:
            raise InternalError({"extra_lesson_id": str(extra_id)})
        return self._extra(extra)

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
    def _apply_rule(rule: ScheduleRule, fields: RuleFields, slot: Slot) -> None:
        rule.group_id = fields.group_id
        rule.lesson_type = fields.lesson_type
        rule.weekday = fields.weekday
        rule.starts_at = slot.starts_at
        rule.ends_at = slot.ends_at
        rule.repeat = fields.repeat
        rule.room = fields.room

    @staticmethod
    def _apply_extra(extra: ExtraLesson, fields: ExtraFields, slot: Slot) -> None:
        extra.group_id = fields.group_id
        extra.lesson_type = fields.lesson_type
        extra.day = fields.day
        extra.starts_at = slot.starts_at
        extra.ends_at = slot.ends_at
        extra.room = fields.room

    @staticmethod
    def _group(group: Group) -> GroupRef:
        return GroupRef(id=group.id, name=group.name)

    @staticmethod
    def _rule(rule: ScheduleRule) -> Rule:
        return Rule(
            id=rule.id,
            group=ScheduleCourseService._group(rule.group),
            lesson_type=rule.lesson_type,
            weekday=rule.weekday,
            slot=ScheduleService.slot_number(rule.starts_at, rule.ends_at),
            starts_at=rule.starts_at,
            ends_at=rule.ends_at,
            repeat=rule.repeat,
            room=rule.room,
        )

    @staticmethod
    def _extra(extra: ExtraLesson) -> Extra:
        return Extra(
            id=extra.id,
            group=ScheduleCourseService._group(extra.group),
            lesson_type=extra.lesson_type,
            day=extra.day,
            slot=ScheduleService.slot_number(extra.starts_at, extra.ends_at),
            starts_at=extra.starts_at,
            ends_at=extra.ends_at,
            room=extra.room,
        )
