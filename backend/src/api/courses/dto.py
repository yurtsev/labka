from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import ScaleType


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
    is_archived: bool
    groups: tuple[GroupRef, ...]
