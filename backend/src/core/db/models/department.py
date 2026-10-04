from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.models.base import Base
from src.core.db.models.faculty import Faculty


class Department(Base):
    __table_args__ = (UniqueConstraint("faculty_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    faculty_id: Mapped[UUID] = mapped_column(ForeignKey("faculties.id"))
    name: Mapped[str]

    faculty: Mapped[Faculty] = relationship(lazy="raise")

    def __str__(self) -> str:
        return self.name
