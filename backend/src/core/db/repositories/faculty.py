from src.core.db.models.faculty import Faculty
from src.core.db.repositories.base import BaseRepository


class FacultyRepository(BaseRepository[Faculty]):
    model = Faculty
