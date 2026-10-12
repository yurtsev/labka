from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Index, false, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.enums import NotificationType
from src.core.db.models.base import Base


class Notification(Base):
    """Личное уведомление. Данные — слепок событий для текста и перехода к объекту.

    О каждой вставке PostgreSQL сообщает по каналу `notifications` (триггер из миграции),
    поэтому WebSocket получает событие только после коммита.
    """

    __table_args__ = (
        Index(None, "user_id", "created_at"),
        # Счётчик непрочитанных и «прочитать все» идут только по непрочитанным.
        Index("ix_notifications_unread", "user_id", postgresql_where=text("NOT is_read")),
        # Пока уведомление не прочитано, такое же по тому же объекту не создаётся второй раз.
        Index(
            "uq_notifications_unread_dedup",
            "user_id",
            "dedup_key",
            unique=True,
            postgresql_where=text("NOT is_read AND dedup_key IS NOT NULL"),
        ),
        # Напоминание о дедлайне — не больше одного на «студент + задание + срок»: после переноса
        # срока напоминание приходит снова.
        Index(
            "uq_notifications_deadline_reminder",
            "user_id",
            text("(data ->> 'assignment_id')"),
            text("(data ->> 'deadline_at')"),
            unique=True,
            postgresql_where=text("type = 'deadline_reminder'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[NotificationType]
    data: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_read: Mapped[bool] = mapped_column(server_default=false())
    dedup_key: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
