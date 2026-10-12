from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.models.assignment import Assignment
from src.core.db.models.base import Base
from src.core.db.models.review import Review
from src.core.db.models.submission_file import SubmissionFile
from src.core.db.models.user import User


class Submission(Base):
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text)
    is_late: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    assignment: Mapped[Assignment] = relationship(lazy="raise")
    student: Mapped[User] = relationship(lazy="raise")
    files: Mapped[list[SubmissionFile]] = relationship(
        order_by=SubmissionFile.id, cascade="all, delete-orphan", lazy="raise"
    )
    review: Mapped[Review | None] = relationship(lazy="raise")
