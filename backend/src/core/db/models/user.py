from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import UserRole
from src.core.db.models.base import Base
from src.core.db.models.department import Department
from src.core.db.models.group import Group


class User(Base):
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint(
            "(role = 'student' AND group_id IS NOT NULL AND department_id IS NULL)"
            " OR (role = 'teacher' AND department_id IS NOT NULL AND group_id IS NULL)"
            " OR (role = 'admin' AND group_id IS NULL AND department_id IS NULL)",
            name="role_links",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    last_name: Mapped[str]
    first_name: Mapped[str]
    middle_name: Mapped[str | None]
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[UserRole]
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("groups.id"), index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"), index=True)
    avatar_key: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    department: Mapped[Department | None] = relationship(lazy="raise")
    group: Mapped[Group | None] = relationship(foreign_keys=[group_id], lazy="raise")
    # Группы, прикреплённые к преподавателю админом; у студента и админа пусто.
    teaching_groups: Mapped[list[Group]] = relationship(secondary="teacher_groups", lazy="raise")
