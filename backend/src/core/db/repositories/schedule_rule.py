from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from src.core.db.models.course import Course
from src.core.db.models.schedule_rule import ScheduleRule
from src.core.db.repositories.base import BaseRepository


class ScheduleRuleRepository(BaseRepository[ScheduleRule]):
    model = ScheduleRule

    async def list_for_course(self, course_id: UUID, group_id: UUID | None) -> list[ScheduleRule]:
        """Правила курса с группами; `group_id` — только правила этой группы."""
        query = select(ScheduleRule).where(ScheduleRule.course_id == course_id)
        if group_id is not None:
            query = query.where(ScheduleRule.group_id == group_id)
        query = query.options(selectinload(ScheduleRule.group)).order_by(
            ScheduleRule.weekday, ScheduleRule.starts_at, ScheduleRule.id
        )
        return list(await self._session.scalars(query))

    async def get_in_course(self, course_id: UUID, rule_id: UUID) -> ScheduleRule | None:
        """Правило курса вместе с группой; объект перечитывается из БД."""
        query = (
            select(ScheduleRule)
            .where(ScheduleRule.id == rule_id, ScheduleRule.course_id == course_id)
            .options(selectinload(ScheduleRule.group))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def list_for_teacher(self, teacher_id: UUID) -> list[ScheduleRule]:
        """Правила неархивных курсов преподавателя с курсами и группами."""
        query = self._active().where(Course.teacher_id == teacher_id)
        return list(await self._session.scalars(query))

    async def list_for_group(self, group_id: UUID) -> list[ScheduleRule]:
        """Правила группы в неархивных курсах с курсами и группами."""
        query = self._active().where(ScheduleRule.group_id == group_id)
        return list(await self._session.scalars(query))

    @staticmethod
    def _active() -> Select[tuple[ScheduleRule]]:
        return (
            select(ScheduleRule)
            .join(Course, Course.id == ScheduleRule.course_id)
            .where(Course.is_archived.is_(False))
            .options(selectinload(ScheduleRule.course), selectinload(ScheduleRule.group))
            .order_by(ScheduleRule.id)
        )
