from src.core.db.models.department import Department
from src.core.db.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department
