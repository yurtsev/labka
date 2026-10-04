from uuid import UUID, uuid7

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.models.base import Base
from src.core.db.models.faculty import Faculty


class Direction(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    faculty_id: Mapped[UUID] = mapped_column(ForeignKey("faculties.id"), index=True)
    short_name: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]

    faculty: Mapped[Faculty] = relationship(lazy="raise")

    def __str__(self) -> str:
        return f"{self.short_name} — {self.name}"
