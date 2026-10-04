from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.models.base import Base


class Submission(Base):
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text)
    is_late: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
