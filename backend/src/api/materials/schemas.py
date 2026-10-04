from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

type ContentType = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
type MaterialTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None


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


class MaterialUpdateRequest(BaseModel):
    title: MaterialTitle
    text: OptionalText = None


class MaterialCreateRequest(MaterialUpdateRequest):
    files: list[UploadedFileRequest] = Field(default_factory=list)


class MaterialFileResponse(BaseModel):
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


class MaterialResponse(BaseModel):
    id: UUID
    title: str
    text: str | None
    created_at: datetime
    updated_at: datetime
    files: list[MaterialFileResponse]
