from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.api.schemas import CourseRefResponse
from src.core.db.enums import NotificationType
from src.core.notifications.enums import NotificationSection


class UnreadCountResponse(BaseModel):
    unread_count: int


class ReadAllResponse(BaseModel):
    marked: int
    unread_count: int


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


class ReadyMessage(BaseModel):
    """Первое сообщение после подключения: сколько уведомлений ждёт прочтения."""

    type: Literal["ready"] = "ready"
    unread_count: int


class NotificationMessage(BaseModel):
    """Новое уведомление и обновлённый счётчик."""

    type: Literal["notification"] = "notification"
    notification: NotificationResponse
    unread_count: int


class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"


class ResyncMessage(BaseModel):
    """Связь с БД прерывалась: что-то могло прийти незамеченным — перечитайте список."""

    type: Literal["resync"] = "resync"
