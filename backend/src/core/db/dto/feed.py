from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class FeedEntryKind(StrEnum):
    ASSIGNMENT = "assignment"
    ANNOUNCEMENT = "announcement"


@dataclass(frozen=True)
class FeedEntryRef:
    """Запись ленты курса: что это и её id; сами данные загружаются отдельно."""

    kind: FeedEntryKind
    id: UUID
