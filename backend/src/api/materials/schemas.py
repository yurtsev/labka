from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.api.schemas import UploadedFileRequest

type MaterialTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None


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
