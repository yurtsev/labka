from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.core.db.enums import ExamType


class FinalGradeRequest(BaseModel):
    """Зачёт — `passed`; дифф. зачёт и экзамен — `grade`. Задаётся ровно одно из двух."""

    grade: int | None = Field(
        default=None,
        strict=True,
        ge=2,
        le=5,
        description="2 — не сдал, 3 — удовл., 4 — хорошо, 5 — отлично",
    )
    passed: bool | None = Field(default=None, strict=True, description="Зачтено или нет")

    @model_validator(mode="after")
    def check_one_result(self) -> Self:
        if (self.grade is None) == (self.passed is None):
            raise ValueError("нужно задать ровно одно: grade или passed")
        return self


class StudentGradeResponse(BaseModel):
    student_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    group_id: UUID
    group_name: str
    # Форма контроля группы; `null`, пока экзамен группе не назначен.
    exam_type: ExamType | None
    grade: int | None
    passed: bool | None
    graded_at: datetime | None


class MyGradeResponse(BaseModel):
    exam_type: ExamType | None
    grade: int | None
    passed: bool | None
    graded_at: datetime | None
