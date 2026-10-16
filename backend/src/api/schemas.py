from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.core.db.enums import SemesterTerm


class SemesterResponse(BaseModel):
    """Семестр: пары идут до `classes_end_on`, до `ends_on` — только сессия."""

    term: SemesterTerm
    year: int
    starts_on: date
    classes_end_on: date
    ends_on: date


class CourseRefResponse(BaseModel):
    id: UUID
    name: str


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
