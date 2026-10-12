from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from src.core.db.enums import LessonType, ScheduleRepeat
from src.core.schedule.dto import Semester, Slot


@dataclass(frozen=True)
class GroupRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class RuleFields:
    """Правило расписания из запроса; время берётся из окна `slot`."""

    group_id: UUID
    lesson_type: LessonType
    weekday: int
    slot: int
    repeat: ScheduleRepeat
    room: str | None


@dataclass(frozen=True)
class ExtraFields:
    """Разовое занятие из запроса; время берётся из окна `slot`."""

    group_id: UUID
    lesson_type: LessonType
    day: date
    slot: int
    room: str | None


@dataclass(frozen=True)
class Rule:
    id: UUID
    group: GroupRef
    lesson_type: LessonType
    weekday: int
    # `None`, если окно пары с тех пор убрали из сетки.
    slot: int | None
    starts_at: time
    ends_at: time
    repeat: ScheduleRepeat
    room: str | None


@dataclass(frozen=True)
class Extra:
    id: UUID
    group: GroupRef
    lesson_type: LessonType
    day: date
    slot: int | None
    starts_at: time
    ends_at: time
    room: str | None


@dataclass(frozen=True)
class CourseSchedule:
    """Расписание курса: у студента — только его группа, у преподавателя — все группы."""

    semester: Semester
    rules: tuple[Rule, ...]
    extras: tuple[Extra, ...]


@dataclass(frozen=True)
class Slots:
    items: tuple[Slot, ...]
