from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints


class AnnouncementRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnnouncementResponse(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    updated_at: datetime
