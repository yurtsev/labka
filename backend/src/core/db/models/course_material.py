from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.models.base import Base
from src.core.db.models.course_material_file import CourseMaterialFile


class CourseMaterial(Base):
    """Материал курса: название, текст в markdown (ссылки — в тексте) и файлы."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str]
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Файлы удаляет каскад в БД: ORM не грузит их ради удаления материала.
    files: Mapped[list[CourseMaterialFile]] = relationship(
        order_by=CourseMaterialFile.id,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
