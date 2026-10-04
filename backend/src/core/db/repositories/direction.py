from src.core.db.models.direction import Direction
from src.core.db.repositories.base import BaseRepository


class DirectionRepository(BaseRepository[Direction]):
    model = Direction
