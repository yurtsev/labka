from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Announcement:
    id: UUID
    text: str
    created_at: datetime
    updated_at: datetime
