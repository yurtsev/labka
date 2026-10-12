from datetime import date, time
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import LessonType
from src.core.db.models.base import Base
from src.core.db.models.course import Course
from src.core.db.models.group import Group


class ExtraLesson(Base):
    """Разовое занятие группы на конкретную дату. Время — настенное время МСК."""

    __table_args__ = (
        # Группу убрали из курса — её разовые занятия удаляются вместе со связью.
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
    lesson_type: Mapped[LessonType]
    day: Mapped[date]
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    room: Mapped[str | None]

    course: Mapped[Course] = relationship(
        primaryjoin="ExtraLesson.course_id == Course.id",
        foreign_keys="ExtraLesson.course_id",
        viewonly=True,
        lazy="raise",
    )
    group: Mapped[Group] = relationship(
        primaryjoin="ExtraLesson.group_id == Group.id",
        foreign_keys="ExtraLesson.group_id",
        viewonly=True,
        lazy="raise",
    )
