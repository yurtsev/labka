from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from src.core.db.enums import LessonType, ScheduleRepeat, SemesterTerm
from src.core.schedule.enums import CalendarView


@dataclass(frozen=True)
class Slot:
    """Окно пары."""

    number: int
    starts_at: time
    ends_at: time


@dataclass(frozen=True)
class Semester:
    """Учебный семестр: пары идут до `classes_end_on`, до `ends_on` — только сессия."""

    term: SemesterTerm
    year: int
    starts_on: date
    classes_end_on: date
    ends_on: date


@dataclass(frozen=True)
class Week:
    """Календарная неделя пн–вс; номер и чётность считаются от начала семестра.

    Вне семестра (например, летние каникулы) номер и чётность — `None`.
    """

    starts_on: date
    ends_on: date
    term: SemesterTerm | None
    number: int | None
    is_even: bool | None


@dataclass(frozen=True)
class LessonRule:
    """Правило расписания курса и семестр этого курса."""

    id: UUID
    course_id: UUID
    group_id: UUID
    semester: Semester
    lesson_type: LessonType
    weekday: int
    starts_at: time
    ends_at: time
    repeat: ScheduleRepeat
    room: str | None


@dataclass(frozen=True)
class ExtraLessonSpec:
    """Разовое занятие на конкретную дату."""

    id: UUID
    course_id: UUID
    group_id: UUID
    lesson_type: LessonType
    day: date
    starts_at: time
    ends_at: time
    room: str | None


@dataclass(frozen=True)
class Occurrence:
    """Занятие на конкретной дате — из правила или разовое."""

    source_id: UUID
    course_id: UUID
    group_id: UUID
    lesson_type: LessonType
    day: date
    starts_at: time
    ends_at: time
    room: str | None
    is_extra: bool


@dataclass(frozen=True)
class Period:
    """Период календаря и даты, на которые переходят стрелки «назад» и «вперёд».

    Месяц показывается целыми неделями пн–вс, поэтому `starts_on` и `ends_on` могут
    выходить за границы месяца. `prev` и `next` у месяца — первые числа соседних месяцев.
    """

    view: CalendarView
    starts_on: date
    ends_on: date
    prev: date
    next: date
