from src.core.db.models.course_material_file import CourseMaterialFile
from src.core.db.repositories.base import BaseRepository


class CourseMaterialFileRepository(BaseRepository[CourseMaterialFile]):
    model = CourseMaterialFile
