from collections.abc import Collection

from src.core.db.models.course_material_file import CourseMaterialFile
from src.core.db.repositories.base import BaseRepository


class CourseMaterialFileRepository(BaseRepository[CourseMaterialFile]):
    model = CourseMaterialFile

    async def attached_keys(self, keys: Collection[str]) -> set[str]:
        """Какие из ключей уже прикреплены к записи."""
        return await self._present(CourseMaterialFile.file_key, keys)
