from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.db.enums import NotificationType, SemesterTerm
from src.core.notifications.enums import NotificationSection


class SemesterResponse(BaseModel):
    """Семестр: пары идут до `classes_end_on`, до `ends_on` — только сессия."""

    term: SemesterTerm
    year: int
    starts_on: date
    classes_end_on: date
    ends_on: date


class CourseRefResponse(BaseModel):
    id: UUID
    name: str


class TargetResponse(BaseModel):
    """Куда вести по уведомлению: раздел и идентификаторы объектов в нём."""

    section: NotificationSection
    course_id: UUID | None
    assignment_id: UUID | None
    submission_id: UUID | None
    student_id: UUID | None
    day: date | None


class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    text: str
    course: CourseRefResponse | None
    target: TargetResponse
    is_read: bool
    created_at: datetime
