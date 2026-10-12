from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.core.db.enums import AssignmentType, ReviewVerdict, ScaleType

type OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None


class GradeSchema(BaseModel):
    """Оценка: `score` для шкалы `range`, `passed` для зачёт/незачёт."""

    score: int | None = None
    passed: bool | None = None


class ReviewCreateRequest(BaseModel):
    verdict: ReviewVerdict
    grade: GradeSchema = Field(default_factory=GradeSchema)
    comment: OptionalText = None


class ReviewCorrectRequest(BaseModel):
    grade: GradeSchema = Field(default_factory=GradeSchema)
    comment: OptionalText = None


class PersonResponse(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None


class NamedResponse(BaseModel):
    id: UUID
    name: str


class AssignmentRefResponse(BaseModel):
    id: UUID
    type: AssignmentType
    title: str


class QueueItemResponse(BaseModel):
    submission_id: UUID
    number: int
    created_at: datetime
    is_late: bool
    student: PersonResponse
    group: NamedResponse
    in_course: bool
    course: NamedResponse
    assignment: AssignmentRefResponse


class ScaleResponse(BaseModel):
    type: ScaleType
    min: int | None
    max: int | None


class AttemptFileResponse(BaseModel):
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


class AttemptReviewResponse(BaseModel):
    verdict: ReviewVerdict
    grade: GradeSchema | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class AttemptResponse(BaseModel):
    id: UUID
    number: int
    comment: str | None
    is_late: bool
    created_at: datetime
    files: list[AttemptFileResponse]
    review: AttemptReviewResponse | None


class StudentAttemptsResponse(BaseModel):
    student: PersonResponse
    assignment: AssignmentRefResponse
    scale: ScaleResponse
    attempts: list[AttemptResponse]
