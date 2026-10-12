from calendar import monthrange
from collections.abc import Collection, Iterator
from datetime import date, time, timedelta

from src.config import cfg
from src.core.db.enums import ScheduleRepeat, SemesterTerm
from src.core.schedule.dto import (
    ExtraLessonSpec,
    LessonRule,
    Occurrence,
    Period,
    Semester,
    Slot,
    Week,
)
from src.core.schedule.enums import CalendarView
from src.core.schedule.exc import SlotNotFoundError


class ScheduleService:
    """Сетка пар, семестры и занятия по правилам. Без I/O."""

    @staticmethod
    def slots() -> tuple[Slot, ...]:
        """Окна пар из конфига по порядку номеров."""
        return tuple(
            Slot(item.number, item.starts_at, item.ends_at)
            for item in sorted(cfg.schedule.slots, key=lambda slot: slot.number)
        )

    @staticmethod
    def slot(number: int) -> Slot:
        """Окно пары по номеру.

        Raises:
            SlotNotFoundError: в сетке нет такой пары.
        """
        for slot in ScheduleService.slots():
            if slot.number == number:
                return slot
        raise SlotNotFoundError({"slot": number})

    @staticmethod
    def slot_number(starts_at: time, ends_at: time) -> int | None:
        """Номер пары по времени; `None`, если сетку с тех пор поменяли и окна больше нет."""
        for slot in ScheduleService.slots():
            if (slot.starts_at, slot.ends_at) == (starts_at, ends_at):
                return slot.number
        return None

    @staticmethod
    def semester(term: SemesterTerm, year: int) -> Semester:
        """Семестр: `year` — календарный год, в котором он начинается.

        Осенний 2026: с 1 сентября 2026 по 31 января 2027.
        """
        settings = cfg.schedule
        if term == SemesterTerm.AUTUMN:
            starts, classes_end, ends = (
                settings.autumn_starts,
                settings.autumn_classes_end,
                settings.autumn_ends,
            )
        else:
            starts, classes_end, ends = (
                settings.spring_starts,
                settings.spring_classes_end,
                settings.spring_ends,
            )
        starts_on = date(year, starts.month, starts.day)
        # Осенний семестр заканчивается в январе следующего года, пары — до конца декабря.
        ends_on = date(year if ends.month >= starts.month else year + 1, ends.month, ends.day)
        classes_end_on = date(
            year if classes_end.month >= starts.month else year + 1,
            classes_end.month,
            classes_end.day,
        )
        return Semester(term, year, starts_on, classes_end_on, ends_on)

    @staticmethod
    def current_semester(today: date) -> Semester:
        """Семестр на дату; летом, между весенним и осенним, — ближайший осенний."""
        for candidate in ScheduleService._around(today):
            if candidate.starts_on <= today <= candidate.ends_on:
                return candidate
        return ScheduleService.semester(SemesterTerm.AUTUMN, today.year)

    @staticmethod
    def week(day: date) -> Week:
        """Неделя пн–вс, в которую попадает дата, с номером и чётностью от начала семестра.

        Неделя 1 — та, в которую попадает дата начала семестра, она нечётная. Если в неделе
        начинается новый семестр, она относится к нему.
        """
        monday = day - timedelta(days=day.weekday())
        sunday = monday + timedelta(days=6)
        found = [
            semester
            for semester in ScheduleService._around(day)
            if ScheduleService._monday(semester.starts_on) <= monday <= semester.ends_on
        ]
        if not found:
            return Week(monday, sunday, None, None, None)
        semester = max(found, key=lambda item: item.starts_on)
        number = ScheduleService._week_number(semester, monday)
        return Week(monday, sunday, semester.term, number, number % 2 == 0)

    @staticmethod
    def period(view: CalendarView, day: date) -> Period:
        """Период календаря, в который попадает дата, и даты для стрелок."""
        match view:
            case CalendarView.DAY:
                return Period(view, day, day, day - timedelta(days=1), day + timedelta(days=1))
            case CalendarView.WEEK:
                monday = ScheduleService._monday(day)
                return Period(
                    view,
                    monday,
                    monday + timedelta(days=6),
                    monday - timedelta(days=7),
                    monday + timedelta(days=7),
                )
            case CalendarView.MONTH:
                first = day.replace(day=1)
                last = first.replace(day=monthrange(day.year, day.month)[1])
                return Period(
                    view,
                    ScheduleService._monday(first),
                    ScheduleService._monday(last) + timedelta(days=6),
                    (first - timedelta(days=1)).replace(day=1),
                    last + timedelta(days=1),
                )

    @staticmethod
    def weeks(first: date, last: date) -> list[Week]:
        """Все недели пн–вс, которые пересекают период."""
        monday = ScheduleService._monday(first)
        found = []
        while monday <= last:
            found.append(ScheduleService.week(monday))
            monday += timedelta(days=7)
        return found

    @staticmethod
    def occurrences(
        rules: Collection[LessonRule],
        extras: Collection[ExtraLessonSpec],
        first: date,
        last: date,
    ) -> list[Occurrence]:
        """Занятия за период по правилам и разовые, по дате и времени."""
        found = [
            Occurrence(
                source_id=rule.id,
                course_id=rule.course_id,
                group_id=rule.group_id,
                lesson_type=rule.lesson_type,
                day=day,
                starts_at=rule.starts_at,
                ends_at=rule.ends_at,
                room=rule.room,
                is_extra=False,
            )
            for day in ScheduleService._days(first, last)
            for rule in rules
            if ScheduleService.applies(rule, day)
        ]
        found.extend(
            Occurrence(
                source_id=extra.id,
                course_id=extra.course_id,
                group_id=extra.group_id,
                lesson_type=extra.lesson_type,
                day=extra.day,
                starts_at=extra.starts_at,
                ends_at=extra.ends_at,
                room=extra.room,
                is_extra=True,
            )
            for extra in extras
            if first <= extra.day <= last
        )
        return sorted(found, key=lambda item: (item.day, item.starts_at, str(item.source_id)))

    @staticmethod
    def applies(rule: LessonRule, day: date) -> bool:
        """Проходит ли занятие по правилу в этот день: день недели, пары идут, чётность."""
        semester = rule.semester
        if day.isoweekday() != rule.weekday:
            return False
        if not semester.starts_on <= day <= semester.classes_end_on:
            return False
        if rule.repeat == ScheduleRepeat.WEEKLY:
            return True
        is_even = ScheduleService._week_number(semester, day) % 2 == 0
        return is_even == (rule.repeat == ScheduleRepeat.EVEN)

    @staticmethod
    def _week_number(semester: Semester, day: date) -> int:
        weeks = (ScheduleService._monday(day) - ScheduleService._monday(semester.starts_on)).days
        return weeks // 7 + 1

    @staticmethod
    def _monday(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @staticmethod
    def _around(day: date) -> list[Semester]:
        """Семестры, которые могут накрывать дату: начавшиеся в прошлом и этом году."""
        return [
            ScheduleService.semester(term, year)
            for year in (day.year - 1, day.year)
            for term in SemesterTerm
        ]

    @staticmethod
    def _days(first: date, last: date) -> Iterator[date]:
        for offset in range((last - first).days + 1):
            yield first + timedelta(days=offset)
