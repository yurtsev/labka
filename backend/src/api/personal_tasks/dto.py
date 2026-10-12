from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID


@dataclass(frozen=True)
class TaskFields:
    title: str
    due_date: date
    due_time: time | None


@dataclass(frozen=True)
class PersonalTask:
    """Личная задача студента; дата и время — по МСК."""

    id: UUID
    title: str
    due_date: date
    due_time: time | None
    is_done: bool
    created_at: datetime
