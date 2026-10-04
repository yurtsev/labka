from datetime import date, datetime, time
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Index, false, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.models.base import Base


class PersonalTask(Base):
    """Личная задача студента. Дата и время — настенные по МСК, не UTC."""

    __table_args__ = (Index(None, "student_id", "due_date"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    due_date: Mapped[date]
    due_time: Mapped[time | None]
    is_done: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
