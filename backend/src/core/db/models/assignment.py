from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.enums import AssignmentType, DeadlineType, ScaleType
from src.core.db.models.base import Base


class Assignment(Base):
    __table_args__ = (
        CheckConstraint(
            "(deadline_type = 'none') = (deadline_at IS NULL)",
            name="deadline",
        ),
        CheckConstraint(
            "(scale_type IS NULL AND scale_min IS NULL AND scale_max IS NULL)"
            " OR (scale_type = 'range' AND scale_min IS NOT NULL AND scale_max IS NOT NULL"
            " AND scale_min < scale_max)"
            " OR (scale_type = 'binary' AND scale_min IS NULL AND scale_max IS NULL)",
            name="scale",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[AssignmentType]
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    deadline_type: Mapped[DeadlineType]
    deadline_at: Mapped[datetime | None] = mapped_column(index=True)
    scale_type: Mapped[ScaleType | None]
    scale_min: Mapped[int | None]
    scale_max: Mapped[int | None]
    grading_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
