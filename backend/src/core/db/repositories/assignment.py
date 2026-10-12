from collections.abc import Collection
from uuid import UUID

from sqlalchemy import exists, func, select, union_all, update
from sqlalchemy.orm import selectinload

from src.core.db.models.assignment import Assignment
from src.core.db.models.assignment_file import AssignmentFile
from src.core.db.models.submission import Submission
from src.core.db.models.submission_file import SubmissionFile
from src.core.db.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    model = Assignment

    async def get_with_files(self, assignment_id: UUID) -> Assignment | None:
        """Задание с файлами; уже загруженный в сессию объект перечитывается из БД."""
        query = (
            select(Assignment)
            .where(Assignment.id == assignment_id)
            .options(selectinload(Assignment.files))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def get_many(self, assignment_ids: Collection[UUID]) -> list[Assignment]:
        if not assignment_ids:
            return []
        query = select(Assignment).where(Assignment.id.in_(assignment_ids))
        return list(await self._session.scalars(query))

    async def count_submissions(self, assignment_id: UUID) -> int:
        query = select(func.count(Submission.id)).where(Submission.assignment_id == assignment_id)
        return await self._session.scalar(query) or 0

    async def file_keys(self, assignment_id: UUID) -> list[str]:
        """Ключи всех файлов задания в S3: файлы преподавателя и файлы всех попыток."""
        own = select(AssignmentFile.file_key).where(AssignmentFile.assignment_id == assignment_id)
        submitted = (
            select(SubmissionFile.file_key)
            .join(Submission, Submission.id == SubmissionFile.submission_id)
            .where(Submission.assignment_id == assignment_id)
        )
        return list(await self._session.scalars(union_all(own, submitted)))

    async def inherits_scale_with_submissions(self, course_id: UUID) -> bool:
        """Есть ли в курсе задание со шкалой курса, по которому уже есть попытки."""
        query = select(
            exists().where(
                Assignment.course_id == course_id,
                Assignment.scale_type.is_(None),
                exists().where(Submission.assignment_id == Assignment.id),
            )
        )
        return bool(await self._session.scalar(query))

    async def touch(self, assignment_id: UUID) -> None:
        """Отмечает, что задание изменилось, хотя его собственные поля прежние."""
        query = (
            update(Assignment).where(Assignment.id == assignment_id).values(updated_at=func.now())
        )
        await self._session.execute(query)
