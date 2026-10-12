from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PendingFilter:
    """Очередь на проверку преподавателя с необязательными фильтрами по курсу и заданию."""

    teacher_id: UUID
    course_id: UUID | None
    assignment_id: UUID | None
