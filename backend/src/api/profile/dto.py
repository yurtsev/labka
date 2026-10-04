from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import UserRole


@dataclass(frozen=True)
class Affiliation:
    """Группа студента или кафедра преподавателя."""

    id: UUID
    name: str


@dataclass(frozen=True)
class Profile:
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    role: UserRole
    group: Affiliation | None
    department: Affiliation | None
    avatar_url: str | None
