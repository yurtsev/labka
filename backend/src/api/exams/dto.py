from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from src.core.db.enums import ExamType


@dataclass(frozen=True)
class GroupRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class ExamFields:
    """Экзамен из запроса; время берётся из окна `slot`."""

    group_id: UUID
    exam_type: ExamType
    day: date
    slot: int
    room: str | None


@dataclass(frozen=True)
class Exam:
    id: UUID
    group: GroupRef
    exam_type: ExamType
    day: date
    # `None`, если окно пары с тех пор убрали из сетки.
    slot: int | None
    starts_at: time
    ends_at: time
    room: str | None
