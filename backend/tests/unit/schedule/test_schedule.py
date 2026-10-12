from datetime import date, time
from uuid import uuid7

import pytest

from src.core.db.enums import LessonType, ScheduleRepeat, SemesterTerm
from src.core.schedule.dto import ExtraLessonSpec, LessonRule
from src.core.schedule.enums import CalendarView
from src.core.schedule.exc import SlotNotFoundError
from src.core.schedule.service import ScheduleService


def rule(
    repeat: ScheduleRepeat, weekday: int, term: SemesterTerm = SemesterTerm.AUTUMN, year: int = 2026
) -> LessonRule:
    return LessonRule(
        id=uuid7(),
        course_id=uuid7(),
        group_id=uuid7(),
        semester=ScheduleService.semester(term, year),
        lesson_type=LessonType.LAB,
        weekday=weekday,
        starts_at=time(9, 30),
        ends_at=time(11, 0),
        repeat=repeat,
        room="Б-101",
    )


@pytest.mark.case(id="SCHEDULE-UNIT-001")
def test_semester_boundaries() -> None:
    autumn = ScheduleService.semester(SemesterTerm.AUTUMN, 2026)
    spring = ScheduleService.semester(SemesterTerm.SPRING, 2027)

    assert (autumn.starts_on, autumn.classes_end_on, autumn.ends_on) == (
        date(2026, 9, 1),
        date(2026, 12, 30),
        date(2027, 1, 31),
    )
    assert (spring.starts_on, spring.classes_end_on, spring.ends_on) == (
        date(2027, 2, 1),
        date(2027, 7, 10),
        date(2027, 7, 10),
    )


@pytest.mark.case(id="SCHEDULE-UNIT-002")
@pytest.mark.parametrize(
    ("today", "term", "year"),
    [
        (date(2026, 9, 1), SemesterTerm.AUTUMN, 2026),
        (date(2026, 12, 31), SemesterTerm.AUTUMN, 2026),
        (date(2027, 1, 31), SemesterTerm.AUTUMN, 2026),
        (date(2027, 2, 1), SemesterTerm.SPRING, 2027),
        (date(2027, 7, 10), SemesterTerm.SPRING, 2027),
        (date(2027, 8, 1), SemesterTerm.AUTUMN, 2027),
    ],
)
def test_current_semester(today: date, term: SemesterTerm, year: int) -> None:
    current = ScheduleService.current_semester(today)

    assert (current.term, current.year) == (term, year)


@pytest.mark.case(id="SCHEDULE-UNIT-003")
def test_week_number_and_parity_count_from_semester_start() -> None:
    first = ScheduleService.week(date(2026, 9, 1))
    second = ScheduleService.week(date(2026, 9, 7))
    third = ScheduleService.week(date(2026, 9, 14))
    spring_first = ScheduleService.week(date(2027, 2, 1))
    last_autumn = ScheduleService.week(date(2027, 1, 31))
    summer = ScheduleService.week(date(2027, 7, 20))

    # Неделя 1 — та, в которую попадает 1 сентября (вт), пн–вс, нечётная.
    assert (first.starts_on, first.ends_on) == (date(2026, 8, 31), date(2026, 9, 6))
    assert (first.number, first.is_even) == (1, False)
    assert (second.number, second.is_even) == (2, True)
    assert (third.number, third.is_even) == (3, False)
    assert (spring_first.term, spring_first.number, spring_first.is_even) == (
        SemesterTerm.SPRING,
        1,
        False,
    )
    assert (last_autumn.term, last_autumn.number) == (SemesterTerm.AUTUMN, 22)
    assert (summer.term, summer.number, summer.is_even) == (None, None, None)


@pytest.mark.case(id="SCHEDULE-UNIT-004")
def test_occurrences_follow_repeat_and_stay_inside_classes() -> None:
    weekly = rule(ScheduleRepeat.WEEKLY, 2)
    even = rule(ScheduleRepeat.EVEN, 2)
    odd = rule(ScheduleRepeat.ODD, 2)

    found = ScheduleService.occurrences(
        [weekly, even, odd], [], date(2026, 8, 31), date(2026, 9, 20)
    )

    by_rule = {
        label: [item.day for item in found if item.source_id == item_rule.id]
        for label, item_rule in [("weekly", weekly), ("even", even), ("odd", odd)]
    }
    assert by_rule["weekly"] == [date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15)]
    assert by_rule["odd"] == [date(2026, 9, 1), date(2026, 9, 15)]
    assert by_rule["even"] == [date(2026, 9, 8)]

    before = ScheduleService.occurrences([weekly], [], date(2026, 8, 1), date(2026, 8, 31))
    last_day = rule(ScheduleRepeat.WEEKLY, 3)  # среда 30 декабря — последний день пар
    through_new_year = ScheduleService.occurrences(
        [last_day, rule(ScheduleRepeat.WEEKLY, 4)], [], date(2026, 12, 28), date(2027, 1, 10)
    )
    assert before == []
    assert [item.day for item in through_new_year] == [date(2026, 12, 30)]


@pytest.mark.case(id="SCHEDULE-UNIT-005")
def test_extra_lessons_are_added_inside_period_only() -> None:
    course_id, group_id = uuid7(), uuid7()
    extras = [
        ExtraLessonSpec(
            uuid7(), course_id, group_id, LessonType.PRACTICE, day, time(15, 10), time(16, 40), None
        )
        for day in (date(2026, 10, 3), date(2026, 10, 20))
    ]

    found = ScheduleService.occurrences([], extras, date(2026, 10, 1), date(2026, 10, 7))

    assert [(item.day, item.is_extra) for item in found] == [(date(2026, 10, 3), True)]


@pytest.mark.case(id="SCHEDULE-UNIT-006")
def test_period_per_view_with_neighbours() -> None:
    day = ScheduleService.period(CalendarView.DAY, date(2026, 10, 14))
    week = ScheduleService.period(CalendarView.WEEK, date(2026, 10, 14))
    month = ScheduleService.period(CalendarView.MONTH, date(2026, 10, 14))
    january = ScheduleService.period(CalendarView.MONTH, date(2027, 1, 20))
    december = ScheduleService.period(CalendarView.MONTH, date(2026, 12, 5))

    assert (day.starts_on, day.ends_on, day.prev, day.next) == (
        date(2026, 10, 14),
        date(2026, 10, 14),
        date(2026, 10, 13),
        date(2026, 10, 15),
    )
    assert (week.starts_on, week.ends_on, week.prev, week.next) == (
        date(2026, 10, 12),
        date(2026, 10, 18),
        date(2026, 10, 5),
        date(2026, 10, 19),
    )
    # Октябрь 2026: 1-е — четверг, 31-е — суббота; сетка — целые недели.
    assert (month.starts_on, month.ends_on) == (date(2026, 9, 28), date(2026, 11, 1))
    assert (month.prev, month.next) == (date(2026, 9, 1), date(2026, 11, 1))
    assert (january.prev, january.next) == (date(2026, 12, 1), date(2027, 2, 1))
    assert (december.prev, december.next) == (date(2026, 11, 1), date(2027, 1, 1))
    assert [week.number for week in ScheduleService.weeks(month.starts_on, month.ends_on)] == [
        5,
        6,
        7,
        8,
        9,
    ]


@pytest.mark.case(id="SCHEDULE-UNIT-007")
def test_slot_grid() -> None:
    assert [(s.number, s.starts_at, s.ends_at) for s in ScheduleService.slots()] == [
        (1, time(9, 30), time(11, 0)),
        (2, time(11, 15), time(12, 45)),
        (3, time(13, 0), time(14, 30)),
        (4, time(15, 10), time(16, 40)),
        (5, time(16, 55), time(18, 25)),
    ]
    assert ScheduleService.slot(2).starts_at == time(11, 15)
    assert ScheduleService.slot_number(time(15, 10), time(16, 40)) == 4
    assert ScheduleService.slot_number(time(9, 0), time(10, 30)) is None
    with pytest.raises(SlotNotFoundError):
        ScheduleService.slot(6)
