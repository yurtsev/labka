from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.core.db.enums import ExamType, NotificationType, ReviewVerdict
from src.core.notifications.enums import NotificationSection


class Payload(BaseModel):
    """Слепок события в БД: из него собираются текст и переход, названия не устаревают.

    Заполняются только поля, нужные типу уведомления.
    """

    model_config = ConfigDict(frozen=True)

    course_id: UUID | None = None
    course_name: str | None = None
    assignment_id: UUID | None = None
    assignment_title: str | None = None
    material_title: str | None = None
    student_id: UUID | None = None
    student_name: str | None = None
    submission_id: UUID | None = None
    attempt: int | None = None
    verdict: ReviewVerdict | None = None
    grade: int | None = None
    passed: bool | None = None
    exam_type: ExamType | None = None
    day: date | None = None
    starts_at: time | None = None
    removed: bool = False
    deadline_at: datetime | None = None


@dataclass(frozen=True)
class CourseRef:
    id: UUID
    name: str


@dataclass(frozen=True)
class Target:
    """Куда вести: раздел и идентификаторы объектов в нём."""

    section: NotificationSection
    course_id: UUID | None = None
    assignment_id: UUID | None = None
    submission_id: UUID | None = None
    student_id: UUID | None = None
    day: date | None = None


@dataclass(frozen=True)
class Rendered:
    title: str
    text: str
    target: Target


@dataclass(frozen=True)
class NotificationView:
    """Уведомление в том виде, в каком его показывает приложение."""

    id: UUID
    type: NotificationType
    title: str
    text: str
    course: CourseRef | None
    target: Target
    is_read: bool
    created_at: datetime
