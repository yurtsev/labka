from typing import Literal

from pydantic import BaseModel

from src.api.schemas import NotificationResponse


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
