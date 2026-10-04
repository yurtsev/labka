from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import ScaleType
from src.core.db.models.base import Base
from src.core.db.models.group import Group
from src.core.db.models.user import User


class Course(Base):
    __table_args__ = (
        CheckConstraint(
            "(scale_type = 'range' AND scale_min IS NOT NULL AND scale_max IS NOT NULL"
            " AND scale_min < scale_max)"
            " OR (scale_type = 'binary' AND scale_min IS NULL AND scale_max IS NULL)",
            name="scale",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    scale_type: Mapped[ScaleType]
    scale_min: Mapped[int | None]
    scale_max: Mapped[int | None]
    grading_note: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    teacher: Mapped[User] = relationship(lazy="raise")
    groups: Mapped[list[Group]] = relationship(
        secondary="course_groups", order_by=Group.name, lazy="raise"
    )
