from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.models.base import Base


class SubmissionFile(Base):
    __table_args__ = (CheckConstraint("file_size >= 0", name="file_size_non_negative"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), index=True
    )
    file_key: Mapped[str] = mapped_column(unique=True)
    file_name: Mapped[str]
    file_size: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
