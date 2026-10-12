from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.models.base import Base


class FinalGrade(Base):
    """Итоговый результат студента по курсу.

    Зачёт — `is_passed` (зачтено или нет); дифференцированный зачёт и экзамен — `grade`:
    2 — не сдал, 3 — удовлетворительно, 4 — хорошо, 5 — отлично. Задано ровно одно из двух.
    """

    __table_args__ = (
        UniqueConstraint("course_id", "student_id"),
        CheckConstraint("grade IS NULL OR grade BETWEEN 2 AND 5", name="grade_range"),
        CheckConstraint("(grade IS NULL) <> (is_passed IS NULL)", name="single_result"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    grade: Mapped[int | None]
    is_passed: Mapped[bool | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
