from uuid import UUID, uuid7

from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.enums import FacultyType
from src.core.db.models.base import Base


class Faculty(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(unique=True)
    short_name: Mapped[str]
    type: Mapped[FacultyType]

    def __str__(self) -> str:
        return self.short_name
