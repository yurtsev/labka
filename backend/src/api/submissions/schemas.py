from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.core.db.enums import ReviewVerdict

type ContentType = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class UploadStartRequest(BaseModel):
    content_type: ContentType
    file_size: Annotated[int, Field(ge=1)]


class UploadFormResponse(BaseModel):
    """Форма для браузера: POST multipart на `url`, все `fields` и файл последним полем `file`."""

    key: str
    url: str
    fields: dict[str, str]


class UploadedFileRequest(BaseModel):
    key: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    file_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]


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
