from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.models.base import Base
from src.core.db.models.group import Group


class GroupInvite(Base):
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    email: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    group: Mapped[Group] = relationship(lazy="raise")
