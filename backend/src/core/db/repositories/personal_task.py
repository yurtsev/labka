from datetime import date
from uuid import UUID

from sqlalchemy import select

from src.core.db.models.personal_task import PersonalTask
from src.core.db.repositories.base import BaseRepository


class PersonalTaskRepository(BaseRepository[PersonalTask]):
    model = PersonalTask

    async def get_own(self, student_id: UUID, task_id: UUID) -> PersonalTask | None:
        """Задача студента; объект перечитывается из БД."""
        query = (
            select(PersonalTask)
            .where(PersonalTask.id == task_id, PersonalTask.student_id == student_id)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def list_between(self, student_id: UUID, first: date, last: date) -> list[PersonalTask]:
        """Задачи студента за период по дате, времени и порядку создания."""
        query = (
            select(PersonalTask)
            .where(
                PersonalTask.student_id == student_id, PersonalTask.due_date.between(first, last)
            )
            .order_by(PersonalTask.due_date, PersonalTask.due_time.nulls_first(), PersonalTask.id)
        )
        return list(await self._session.scalars(query))
