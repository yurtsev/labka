from collections.abc import Collection

from src.core.db.models.submission_file import SubmissionFile
from src.core.db.repositories.base import BaseRepository


class SubmissionFileRepository(BaseRepository[SubmissionFile]):
    model = SubmissionFile

    async def attached_keys(self, keys: Collection[str]) -> set[str]:
        """Какие из ключей уже прикреплены к записи."""
        return await self._present(SubmissionFile.file_key, keys)
