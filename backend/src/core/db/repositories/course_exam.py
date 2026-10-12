from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from src.core.db.models.course import Course
from src.core.db.models.course_exam import CourseExam
from src.core.db.repositories.base import BaseRepository


class CourseExamRepository(BaseRepository[CourseExam]):
    model = CourseExam

    async def list_for_course(self, course_id: UUID, group_id: UUID | None) -> list[CourseExam]:
        """Экзамены курса с группами по дате; `group_id` — только этой группы."""
        query = select(CourseExam).where(CourseExam.course_id == course_id)
        if group_id is not None:
            query = query.where(CourseExam.group_id == group_id)
        query = query.options(selectinload(CourseExam.group)).order_by(
            CourseExam.day, CourseExam.starts_at, CourseExam.id
        )
        return list(await self._session.scalars(query))

    async def get_in_course(self, course_id: UUID, exam_id: UUID) -> CourseExam | None:
        """Экзамен курса вместе с группой; объект перечитывается из БД."""
        query = (
            select(CourseExam)
            .where(CourseExam.id == exam_id, CourseExam.course_id == course_id)
            .options(selectinload(CourseExam.group))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def get_for_group(self, course_id: UUID, group_id: UUID) -> CourseExam | None:
        """Экзамен группы в курсе."""
        query = select(CourseExam).where(
            CourseExam.course_id == course_id, CourseExam.group_id == group_id
        )
        return await self._session.scalar(query)

    async def list_for_teacher(self, teacher_id: UUID, first: date, last: date) -> list[CourseExam]:
        """Экзамены за период в неархивных курсах преподавателя."""
        query = self._active(first, last).where(Course.teacher_id == teacher_id)
        return list(await self._session.scalars(query))

    async def list_for_group(self, group_id: UUID, first: date, last: date) -> list[CourseExam]:
        """Экзамены группы за период в неархивных курсах."""
        query = self._active(first, last).where(CourseExam.group_id == group_id)
        return list(await self._session.scalars(query))

    @staticmethod
    def _active(first: date, last: date) -> Select[tuple[CourseExam]]:
        return (
            select(CourseExam)
            .join(Course, Course.id == CourseExam.course_id)
            .where(Course.is_archived.is_(False), CourseExam.day.between(first, last))
            .options(selectinload(CourseExam.course), selectinload(CourseExam.group))
            .order_by(CourseExam.id)
        )
