from math import ceil
from uuid import UUID

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import selectinload

from src.core.db.dto.feed import FeedEntryKind, FeedEntryRef
from src.core.db.dto.page import Page, PageRequest
from src.core.db.enums import AssignmentType
from src.core.db.models.announcement import Announcement
from src.core.db.models.assignment import Assignment
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

    async def feed_page(
        self, course_id: UUID, assignment_type: AssignmentType | None, page: PageRequest
    ) -> Page[FeedEntryRef]:
        """Лента курса: задания и объявления вперемешку, новые первыми.

        С фильтром по типу задания в ленте только задания этого типа.
        """
        assignments = select(
            literal(FeedEntryKind.ASSIGNMENT.value).label("kind"),
            Assignment.id.label("id"),
            Assignment.created_at.label("created_at"),
        ).where(Assignment.course_id == course_id)
        if assignment_type is not None:
            entries = assignments.where(Assignment.type == assignment_type).subquery()
        else:
            announcements = select(
                literal(FeedEntryKind.ANNOUNCEMENT.value).label("kind"),
                Announcement.id.label("id"),
                Announcement.created_at.label("created_at"),
            ).where(Announcement.course_id == course_id)
            entries = union_all(assignments, announcements).subquery()

        total = await self._session.scalar(select(func.count()).select_from(entries)) or 0
        rows = await self._session.execute(
            select(entries.c.kind, entries.c.id)
            .order_by(entries.c.created_at.desc(), entries.c.id.desc())
            .offset((page.page - 1) * page.per_page)
            .limit(page.per_page)
        )
        return Page(
            items=tuple(FeedEntryRef(kind=FeedEntryKind(kind), id=id) for kind, id in rows),
            page=page.page,
            per_page=page.per_page,
            total=total,
            pages=max(1, ceil(total / page.per_page)),
        )
