from dataclasses import dataclass
from datetime import datetime

from src.core.db.enums import ScaleType
from src.core.grading.enums import ProgressStatus


@dataclass(frozen=True)
class Scale:
    type: ScaleType
    min: int | None
    max: int | None


@dataclass(frozen=True)
class Grade:
    """Оценка: `score` для шкалы `range` или `passed` для `binary`."""

    score: int | None
    passed: bool | None

    @property
    def is_set(self) -> bool:
        return self.score is not None or self.passed is not None


@dataclass(frozen=True)
class Progress:
    """Положение студента по заданию."""

    status: ProgressStatus
    # Оценка из последней проверенной попытки, где она выставлена.
    grade: Grade | None
    attempts: int
    last_submitted_at: datetime | None
    last_is_late: bool


@dataclass(frozen=True)
class Summary:
    """Сводка по заданию среди студентов курса: «сдали 14/25 · ждут проверки 3 · приняты 9»."""

    students: int
    submitted: int
    on_review: int
    accepted: int
