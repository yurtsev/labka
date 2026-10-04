from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TeacherFields:
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    department_id: UUID
    group_ids: frozenset[UUID]


@dataclass(frozen=True)
class CreatedTeacher:
    teacher_id: UUID
    password: str
