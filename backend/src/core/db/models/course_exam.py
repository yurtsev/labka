from datetime import date, time
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import ExamType
from src.core.db.models.base import Base
from src.core.db.models.course import Course
from src.core.db.models.group import Group


class CourseExam(Base):
    """Итоговый контроль курса для группы: зачёт, дифференцированный зачёт или экзамен.

    У группы в курсе он один. Время — настенное время МСК, окно пары.
    """

    __table_args__ = (
        UniqueConstraint("course_id", "group_id"),
        # Группу убрали из курса — её экзамен удаляется вместе со связью.
        ForeignKeyConstraint(
            ["course_id", "group_id"],
            ["course_groups.course_id", "course_groups.group_id"],
            ondelete="CASCADE",
        ),
        Index(None, "group_id"),
        CheckConstraint("starts_at < ends_at", name="time_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    course_id: Mapped[UUID]
    group_id: Mapped[UUID]
    exam_type: Mapped[ExamType]
    day: Mapped[date]
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    room: Mapped[str | None]

    course: Mapped[Course] = relationship(
        primaryjoin="CourseExam.course_id == Course.id",
        foreign_keys="CourseExam.course_id",
        viewonly=True,
        lazy="raise",
    )
    group: Mapped[Group] = relationship(
        primaryjoin="CourseExam.group_id == Group.id",
        foreign_keys="CourseExam.group_id",
        viewonly=True,
        lazy="raise",
    )
