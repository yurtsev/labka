from src.core.db.models.review import Review
from src.core.db.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    model = Review
