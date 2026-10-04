from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import FacultyType


@dataclass(frozen=True)
class FacultyFields:
    name: str
    short_name: str
    type: FacultyType


@dataclass(frozen=True)
class DepartmentFields:
    faculty_id: UUID
    name: str


@dataclass(frozen=True)
class DirectionFields:
    faculty_id: UUID
    short_name: str
    name: str
