from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.enums import ReviewVerdict
from src.core.db.models.base import Base


class Review(Base):
    """Проверка попытки.

    Вердикт и оценка независимы: `accepted` требует оценку, но не определяет её значение.
    Оценка — `score` для шкалы `range` или `is_passed` для `binary`, не обе сразу.
    """

    __table_args__ = (
        CheckConstraint("score IS NULL OR is_passed IS NULL", name="single_grade"),
        CheckConstraint(
            "verdict <> 'accepted' OR score IS NOT NULL OR is_passed IS NOT NULL",
            name="accepted_has_grade",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True
    )
    verdict: Mapped[ReviewVerdict]
    score: Mapped[int | None]
    is_passed: Mapped[bool | None]
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
