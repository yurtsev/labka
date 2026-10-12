from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from src.api.calendar.enums import CalendarItemKind
from src.core.db.enums import AssignmentType, DeadlineType, ExamType, LessonType
from src.core.grading.enums import ProgressStatus
from src.core.schedule.dto import Period, Week


@dataclass(frozen=True)
class CourseRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class GroupRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class CalendarLesson:
    course: CourseRef
    group: GroupRef
    lesson_type: LessonType
    # `None`, если окно пары с тех пор убрали из сетки.
    slot: int | None
    room: str | None
    # Разовое занятие, а не по правилу расписания.
    is_extra: bool


@dataclass(frozen=True)
class CalendarExam:
    course: CourseRef
    group: GroupRef
    exam_type: ExamType
    slot: int | None
    room: str | None


@dataclass(frozen=True)
class CalendarDeadline:
    assignment_id: UUID
    title: str
    type: AssignmentType
    deadline_type: DeadlineType
    course: CourseRef
    # Статус сдачи — у студента; у преподавателя `None`.
    my_status: ProgressStatus | None


@dataclass(frozen=True)
class CalendarTask:
    id: UUID
    title: str
    is_done: bool


@dataclass(frozen=True)
class CalendarItem:
    """Событие календаря; день и время — по МСК. Без времени — событие на весь день."""

    kind: CalendarItemKind
    day: date
    starts_at: time | None
    ends_at: time | None
    lesson: CalendarLesson | None
    exam: CalendarExam | None
    deadline: CalendarDeadline | None
    task: CalendarTask | None


@dataclass(frozen=True)
class Calendar:
    period: Period
    weeks: tuple[Week, ...]
    items: tuple[CalendarItem, ...]
