from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Index, false, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.enums import NotificationType
from src.core.db.models.base import Base


class Notification(Base):
    __table_args__ = (
        Index(None, "user_id", "created_at"),
        # Напоминание о дедлайне — не больше одного на пару «студент + задание».
        Index(
            "uq_notifications_deadline_reminder",
            "user_id",
            text("(data ->> 'assignment_id')"),
            unique=True,
            postgresql_where=text("type = 'deadline_reminder'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[NotificationType]
    data: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_read: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
