from sqlalchemy import select

from src.core.db.models.group_invite import GroupInvite
from src.core.db.repositories.base import BaseRepository


class GroupInviteRepository(BaseRepository[GroupInvite]):
    model = GroupInvite

    async def get_by_email(self, email: str) -> GroupInvite | None:
        return await self._session.scalar(select(GroupInvite).where(GroupInvite.email == email))
