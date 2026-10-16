from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.grading.enums import ProgressStatus


@dataclass(frozen=True)
class StudentProgressFilter:
    """Таблица студентов курса по заданию с необязательными фильтрами."""

    assignment_id: UUID
    group_id: UUID | None
    status: ProgressStatus | None


@dataclass(frozen=True)
class ProgressRow:
    """Положение студента по заданию, посчитанное в БД по его попыткам и проверкам.

    Оценка — из последней проверенной попытки, где она выставлена.
    """

    assignment_id: UUID
    student_id: UUID
    status: ProgressStatus
    attempts: int
    first_submitted_at: datetime | None
    last_submitted_at: datetime | None
    last_is_late: bool
    grade_score: int | None
    grade_passed: bool | None


@dataclass(frozen=True)
class SummaryRow:
    """Сколько студентов курса сдали задание, ждут проверки и приняты."""

    assignment_id: UUID
    submitted: int
    on_review: int
    accepted: int


@dataclass(frozen=True)
class StudentProgress:
    """Строка таблицы студентов по заданию."""

    student_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    group_id: UUID
    group_name: str
    progress: ProgressRow
