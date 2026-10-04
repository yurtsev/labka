from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import StudyForm, StudyLevel
from src.core.db.models.base import Base
from src.core.db.models.direction import Direction


class Group(Base):
    __table_args__ = (
        CheckConstraint("number > 0", name="number_positive"),
        CheckConstraint("admission_year BETWEEN 1900 AND 2999", name="admission_year_range"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    direction_id: Mapped[UUID] = mapped_column(ForeignKey("directions.id"), index=True)
    level: Mapped[StudyLevel]
    study_form: Mapped[StudyForm]
    admission_year: Mapped[int]
    number: Mapped[int]
    name: Mapped[str] = mapped_column(unique=True)
    registration_code_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(server_default=true())

    direction: Mapped[Direction] = relationship(lazy="raise")

    def __str__(self) -> str:
        return self.name
