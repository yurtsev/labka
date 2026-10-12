from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.db.dto.feed import FeedEntryKind
from src.core.db.enums import AssignmentType, DeadlineType
from src.core.grading.dto import Progress, Summary


@dataclass(frozen=True)
class FeedAssignment:
    """Задание в ленте: у студента — его статус и оценка, у преподавателя — сводка."""

    id: UUID
    type: AssignmentType
    title: str
    deadline_type: DeadlineType
    deadline_at: datetime | None
    created_at: datetime
    my_progress: Progress | None
    summary: Summary | None


@dataclass(frozen=True)
class FeedAnnouncement:
    id: UUID
    text: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FeedEntry:
    kind: FeedEntryKind
    assignment: FeedAssignment | None
    announcement: FeedAnnouncement | None
