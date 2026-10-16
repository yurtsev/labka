from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.core.db.enums import UserRole


class AvatarUploadStartRequest(BaseModel):
    content_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    file_size: Annotated[int, Field(ge=1)]


class AvatarSetRequest(BaseModel):
    key: Annotated[str, StringConstraints(min_length=1, max_length=512)]


class AffiliationResponse(BaseModel):
    id: UUID
    name: str


class ProfileResponse(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    role: UserRole
    group: AffiliationResponse | None
    department: AffiliationResponse | None
    avatar_url: str | None
