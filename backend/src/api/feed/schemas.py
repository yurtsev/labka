from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, PlainSerializer

from src.core.db.dto.feed import FeedEntryKind
from src.core.db.enums import AssignmentType, DeadlineType
from src.core.grading.enums import ProgressStatus
from src.core.utils.moscow_time import to_moscow

type DeadlineOut = Annotated[datetime, PlainSerializer(to_moscow, return_type=datetime)]


class GradeResponse(BaseModel):
    score: int | None
    passed: bool | None


class ProgressResponse(BaseModel):
    status: ProgressStatus
    grade: GradeResponse | None
    attempts: int
    last_submitted_at: datetime | None
    last_is_late: bool


class SummaryResponse(BaseModel):
    students: int
    submitted: int
    on_review: int
    accepted: int


class FeedAssignmentResponse(BaseModel):
    id: UUID
    type: AssignmentType
    title: str
    deadline_type: DeadlineType
    deadline_at: DeadlineOut | None
    created_at: datetime
    my_progress: ProgressResponse | None
    summary: SummaryResponse | None


class FeedAnnouncementResponse(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    updated_at: datetime


class FeedEntryResponse(BaseModel):
    """Запись ленты: заполнено `assignment` или `announcement` — по `kind`."""

    kind: FeedEntryKind
    assignment: FeedAssignmentResponse | None
    announcement: FeedAnnouncementResponse | None
