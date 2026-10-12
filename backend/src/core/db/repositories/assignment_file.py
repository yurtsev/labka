from collections.abc import Collection

from src.core.db.models.assignment_file import AssignmentFile
from src.core.db.repositories.base import BaseRepository


class AssignmentFileRepository(BaseRepository[AssignmentFile]):
    model = AssignmentFile

    async def attached_keys(self, keys: Collection[str]) -> set[str]:
        """Какие из ключей уже прикреплены к записи."""
        return await self._present(AssignmentFile.file_key, keys)
