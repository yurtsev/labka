from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.api.schemas import UploadedFileRequest
from src.core.db.enums import ReviewVerdict


class SubmissionCreateRequest(BaseModel):
    """Попытка: файлы и/или комментарий; пустую отправить нельзя."""

    comment: Annotated[str, StringConstraints(strip_whitespace=True)] | None = None
    files: list[UploadedFileRequest] = Field(default_factory=list)


class AttemptFileResponse(BaseModel):
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


class GradeResponse(BaseModel):
    score: int | None
    passed: bool | None


class AttemptReviewResponse(BaseModel):
    verdict: ReviewVerdict
    grade: GradeResponse | None
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


class AttemptsResponse(BaseModel):
    items: list[AttemptResponse]
