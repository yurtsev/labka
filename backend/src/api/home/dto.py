from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from src.core.db.enums import AssignmentType, DeadlineType, LessonType
from src.core.grading.enums import ProgressStatus


@dataclass(frozen=True)
class CourseRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class GroupRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class TeacherRef:
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None


@dataclass(frozen=True)
class HomeDeadline:
    """Задание, по которому студенту ещё нужно сдавать работу."""

    assignment_id: UUID
    title: str
    type: AssignmentType
    deadline_type: DeadlineType
    deadline_at: datetime
    course: CourseRef
    teacher: TeacherRef
    status: ProgressStatus


@dataclass(frozen=True)
class HomeLesson:
    day: date
    starts_at: time
    ends_at: time
    # `None`, если окно пары с тех пор убрали из сетки.
    slot: int | None
    lesson_type: LessonType
    room: str | None
    is_extra: bool
    course: CourseRef
    group: GroupRef


@dataclass(frozen=True)
class HomeCourse:
    """Карточка курса на главной."""

    id: UUID
    name: str
    teacher: TeacherRef
    groups: tuple[GroupRef, ...]
    # Студенту — сколько заданий он ещё не сдавал; преподавателю — сколько попыток ждут проверки.
    not_submitted: int | None
    pending_reviews: int | None


@dataclass(frozen=True)
class Home:
    """Главная. Студент: ближайший дедлайн и следующие за ним. Преподаватель: число работ
    на проверке. Занятия и курсы есть у обоих."""

    nearest_deadline: HomeDeadline | None
    upcoming_deadlines: tuple[HomeDeadline, ...]
    pending_reviews: int | None
    upcoming_lessons: tuple[HomeLesson, ...]
    courses: tuple[HomeCourse, ...]
    courses_total: int
