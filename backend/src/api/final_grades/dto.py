from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.db.enums import ExamType


@dataclass(frozen=True)
class FinalResult:
    """Итоговый результат: зачёт — `passed`, дифф. зачёт и экзамен — оценка 2–5."""

    grade: int | None
    passed: bool | None


@dataclass(frozen=True)
class StudentGrade:
    """Студент курса и его итоговый результат.

    `exam_type` — форма контроля его группы, `None`, если она ещё не назначена;
    результат не выставлен, когда `grade` и `passed` пусты.
    """

    student_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    group_id: UUID
    group_name: str
    exam_type: ExamType | None
    grade: int | None
    passed: bool | None
    graded_at: datetime | None


@dataclass(frozen=True)
class MyGrade:
    exam_type: ExamType | None
    grade: int | None
    passed: bool | None
    graded_at: datetime | None
