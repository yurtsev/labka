from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.db.dto.page import Page, PageRequest
from src.core.db.models.course import Course
from src.core.db.models.course_group import CourseGroup
from src.core.db.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    model = Course

    async def get_with_details(self, course_id: UUID) -> Course | None:
        """Курс вместе с преподавателем и группами."""
        query = (
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.teacher), selectinload(Course.groups))
        )
        return await self._session.scalar(query)

    async def page_for_teacher(
        self, teacher_id: UUID, archived: bool, page: PageRequest
    ) -> Page[Course]:
        query = (
            select(Course)
            .where(Course.teacher_id == teacher_id, Course.is_archived.is_(archived))
            .options(selectinload(Course.teacher), selectinload(Course.groups))
        )
        return await self._page(query, page, Course.id.desc())

    async def page_for_group(
        self, group_id: UUID, archived: bool, page: PageRequest
    ) -> Page[Course]:
        query = (
            select(Course)
            .join(CourseGroup, CourseGroup.course_id == Course.id)
            .where(CourseGroup.group_id == group_id, Course.is_archived.is_(archived))
            .options(selectinload(Course.teacher), selectinload(Course.groups))
        )
        return await self._page(query, page, Course.id.desc())

    async def has_group(self, course_id: UUID, group_id: UUID) -> bool:
        query = select(CourseGroup).where(
            CourseGroup.course_id == course_id, CourseGroup.group_id == group_id
        )
        return await self._session.scalar(query) is not None
