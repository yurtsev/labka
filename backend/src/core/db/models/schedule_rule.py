from datetime import time
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.enums import LessonType, ScheduleRepeat
from src.core.db.models.base import Base
from src.core.db.models.course import Course
from src.core.db.models.group import Group


class ScheduleRule(Base):
    """Правило расписания. Время начала и конца — настенное время МСК, не UTC."""

    __table_args__ = (
        # Группу убрали из курса — её правила удаляются вместе со связью.
        ForeignKeyConstraint(
            ["course_id", "group_id"],
            ["course_groups.course_id", "course_groups.group_id"],
            ondelete="CASCADE",
        ),
        Index(None, "group_id"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday_iso"),
        CheckConstraint("starts_at < ends_at", name="time_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    course_id: Mapped[UUID]
    group_id: Mapped[UUID]
    lesson_type: Mapped[LessonType]
    weekday: Mapped[int]
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    repeat: Mapped[ScheduleRepeat]
    room: Mapped[str | None]

    course: Mapped[Course] = relationship(
        primaryjoin="ScheduleRule.course_id == Course.id",
        foreign_keys="ScheduleRule.course_id",
        viewonly=True,
        lazy="raise",
    )
    group: Mapped[Group] = relationship(
        primaryjoin="ScheduleRule.group_id == Group.id",
        foreign_keys="ScheduleRule.group_id",
        viewonly=True,
        lazy="raise",
    )
