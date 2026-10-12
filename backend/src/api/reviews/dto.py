from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.db.enums import AssignmentType, ReviewVerdict
from src.core.grading.dto import Grade, Scale


@dataclass(frozen=True)
class ReviewDecision:
    """Проверка попытки: вердикт, оценка по шкале задания и комментарий."""

    verdict: ReviewVerdict
    grade: Grade
    comment: str | None


@dataclass(frozen=True)
class ReviewCorrection:
    """Исправление проверки: вердикт прежний, меняются оценка и комментарий."""

    grade: Grade
    comment: str | None


@dataclass(frozen=True)
class PersonRef:
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None


@dataclass(frozen=True)
class NamedRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class AssignmentRef:
    id: UUID
    type: AssignmentType
    title: str


@dataclass(frozen=True)
class QueueItem:
    """Попытка, которая ждёт проверки.

    `in_course` ложно, если студента перевели в группу не из курса или его группу убрали.
    """

    submission_id: UUID
    number: int
    created_at: datetime
    is_late: bool
    student: PersonRef
    group: NamedRef
    in_course: bool
    course: NamedRef
    assignment: AssignmentRef


@dataclass(frozen=True)
class QueueFilter:
    course_id: UUID | None
    assignment_id: UUID | None


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
class StudentAttempts:
    """Экран проверки: студент, задание со шкалой и все его попытки, новые первыми."""

    student: PersonRef
    assignment: AssignmentRef
    scale: Scale
    attempts: tuple[Attempt, ...]
