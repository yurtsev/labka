from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Select, select

from src.core.db.dto.group import GroupSearch
from src.core.db.dto.page import Page, PageRequest
from src.core.db.models.group import Group
from src.core.db.models.teacher_group import TeacherGroup
from src.core.db.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    model = Group

    async def get_by_registration_code_hash(self, code_hash: str) -> Group | None:
        query = select(Group).where(Group.registration_code_hash == code_hash)
        return await self._session.scalar(query)

    async def names_taken(self, names: Collection[str]) -> list[str]:
        """Какие из названий уже заняты группами, по алфавиту."""
        if not names:
            return []
        query = select(Group.name).where(Group.name.in_(names)).order_by(Group.name)
        return list(await self._session.scalars(query))

    async def list_all(self) -> list[Group]:
        """Все группы по названию."""
        return list(await self._session.scalars(select(Group).order_by(Group.name)))

    async def list_active(self) -> list[Group]:
        """Активные группы по названию."""
        query = select(Group).where(Group.is_active.is_(True)).order_by(Group.name)
        return list(await self._session.scalars(query))

    async def get_many(self, group_ids: Collection[UUID]) -> list[Group]:
        if not group_ids:
            return []
        query = select(Group).where(Group.id.in_(group_ids)).order_by(Group.name)
        return list(await self._session.scalars(query))

    async def list_attached_to_teacher(
        self, teacher_id: UUID, group_ids: Collection[UUID]
    ) -> list[Group]:
        """Те из `group_ids`, что прикреплены к преподавателю и активны."""
        query = (
            self._attached_to_teacher(teacher_id)
            .where(Group.id.in_(group_ids))
            .order_by(Group.name)
        )
        return list(await self._session.scalars(query))

    async def page_attached_to_teacher(
        self, teacher_id: UUID, search: GroupSearch, page: PageRequest
    ) -> Page[Group]:
        """Активные прикреплённые к преподавателю группы по поиску, по алфавиту."""
        query = self._attached_to_teacher(teacher_id)
        if search.query:
            query = query.where(Group.name.icontains(search.query, autoescape=True))
        if search.level is not None:
            query = query.where(Group.level == search.level)
        if search.study_form is not None:
            query = query.where(Group.study_form == search.study_form)
        if search.admission_year is not None:
            query = query.where(Group.admission_year == search.admission_year)
        return await self._page(query, page, Group.name, Group.id)

    @staticmethod
    def _attached_to_teacher(teacher_id: UUID) -> Select[tuple[Group]]:
        return (
            select(Group)
            .join(TeacherGroup, TeacherGroup.group_id == Group.id)
            .where(TeacherGroup.teacher_id == teacher_id, Group.is_active.is_(True))
        )
