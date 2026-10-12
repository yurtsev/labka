from sqlalchemy import select

from src.core.db.models.direction import Direction
from src.core.db.repositories.base import BaseRepository


class DirectionRepository(BaseRepository[Direction]):
    model = Direction

    async def list_all(self) -> list[Direction]:
        """Все направления по сокращению."""
        return list(await self._session.scalars(select(Direction).order_by(Direction.short_name)))
