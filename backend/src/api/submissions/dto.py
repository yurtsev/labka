from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.db.enums import ReviewVerdict
from src.core.grading.dto import Grade


@dataclass(frozen=True)
class UploadedFile:
    """Файл, который браузер уже загрузил в S3 по форме бэкенда."""

    key: str
    file_name: str


@dataclass(frozen=True)
class AttemptFile:
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


@dataclass(frozen=True)
class AttemptReview:
    verdict: ReviewVerdict
    grade: Grade | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Attempt:
    id: UUID
    number: int
    comment: str | None
    is_late: bool
    created_at: datetime
    files: tuple[AttemptFile, ...]
    review: AttemptReview | None


@dataclass(frozen=True)
class Attempts:
    """История попыток, новые первыми."""

    items: tuple[Attempt, ...]
