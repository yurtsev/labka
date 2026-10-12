from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from src.core.db.models.course import Course
from src.core.db.models.extra_lesson import ExtraLesson
from src.core.db.repositories.base import BaseRepository


class ExtraLessonRepository(BaseRepository[ExtraLesson]):
    model = ExtraLesson

    async def list_for_course(self, course_id: UUID, group_id: UUID | None) -> list[ExtraLesson]:
        """Разовые занятия курса с группами; `group_id` — только этой группы."""
        query = select(ExtraLesson).where(ExtraLesson.course_id == course_id)
        if group_id is not None:
            query = query.where(ExtraLesson.group_id == group_id)
        query = query.options(selectinload(ExtraLesson.group)).order_by(
            ExtraLesson.day, ExtraLesson.starts_at, ExtraLesson.id
        )
        return list(await self._session.scalars(query))

    async def get_in_course(self, course_id: UUID, extra_id: UUID) -> ExtraLesson | None:
        """Разовое занятие курса вместе с группой; объект перечитывается из БД."""
        query = (
            select(ExtraLesson)
            .where(ExtraLesson.id == extra_id, ExtraLesson.course_id == course_id)
            .options(selectinload(ExtraLesson.group))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def list_for_teacher(
        self, teacher_id: UUID, first: date, last: date
    ) -> list[ExtraLesson]:
        """Разовые занятия за период в неархивных курсах преподавателя."""
        query = self._active(first, last).where(Course.teacher_id == teacher_id)
        return list(await self._session.scalars(query))

    async def list_for_group(self, group_id: UUID, first: date, last: date) -> list[ExtraLesson]:
        """Разовые занятия группы за период в неархивных курсах."""
        query = self._active(first, last).where(ExtraLesson.group_id == group_id)
        return list(await self._session.scalars(query))

    @staticmethod
    def _active(first: date, last: date) -> Select[tuple[ExtraLesson]]:
        return (
            select(ExtraLesson)
            .join(Course, Course.id == ExtraLesson.course_id)
            .where(Course.is_archived.is_(False), ExtraLesson.day.between(first, last))
            .options(selectinload(ExtraLesson.course), selectinload(ExtraLesson.group))
            .order_by(ExtraLesson.id)
        )
