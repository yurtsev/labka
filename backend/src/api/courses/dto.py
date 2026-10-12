from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import ScaleType, SemesterTerm
from src.core.schedule.dto import Semester


@dataclass(frozen=True)
class Scale:
    type: ScaleType
    min: int | None
    max: int | None


@dataclass(frozen=True)
class CourseFields:
    """Редактируемые поля курса."""

    name: str
    description: str | None
    scale: Scale
    grading_note: str | None


@dataclass(frozen=True)
class SemesterChoice:
    """Семестр курса, выбранный при создании."""

    term: SemesterTerm
    year: int


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
class CourseDetails:
    id: UUID
    name: str
    description: str | None
    teacher: TeacherRef
    semester: Semester
    scale: Scale
    grading_note: str | None
    is_archived: bool
    groups: tuple[GroupRef, ...]


@dataclass(frozen=True)
class CoursePreview:
    """Плитка курса в списке; полная карточка — `CourseDetails`."""

    id: UUID
    name: str
    teacher: TeacherRef
    semester: Semester
    is_archived: bool
    groups: tuple[GroupRef, ...]
    # Сколько попыток ждут проверки; только у преподавателя, у студента — `None`.
    pending_reviews: int | None
