from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select

from src.core.db.models.announcement import Announcement
from src.core.db.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository[Announcement]):
    model = Announcement

    async def get_many(self, announcement_ids: Collection[UUID]) -> list[Announcement]:
        if not announcement_ids:
            return []
        query = select(Announcement).where(Announcement.id.in_(announcement_ids))
        return list(await self._session.scalars(query))

    async def get_fresh(self, announcement_id: UUID) -> Announcement | None:
        """Объявление, перечитанное из БД, даже если оно уже загружено в сессию."""
        query = (
            select(Announcement)
            .where(Announcement.id == announcement_id)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)
