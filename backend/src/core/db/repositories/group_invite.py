from collections.abc import Sequence
from uuid import UUID, uuid7

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.core.db.models.group_invite import GroupInvite
from src.core.db.repositories.base import BaseRepository


class GroupInviteRepository(BaseRepository[GroupInvite]):
    model = GroupInvite

    async def add_new(self, items: Sequence[tuple[UUID, str]]) -> set[str]:
        """Добавляет почты в списки групп; возвращает те, что действительно добавлены.

        Почта, которая уже есть в списке любой группы, пропускается: это решает сама БД.
        """
        if not items:
            return set()
        statement = (
            insert(GroupInvite)
            .values(
                [{"id": uuid7(), "group_id": group_id, "email": email} for group_id, email in items]
            )
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(GroupInvite.email)
        )
        return set((await self._session.scalars(statement)).all())

    async def get_by_email(self, email: str) -> GroupInvite | None:
        return await self._session.scalar(select(GroupInvite).where(GroupInvite.email == email))
