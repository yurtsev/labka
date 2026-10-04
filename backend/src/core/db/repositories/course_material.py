from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from src.core.db.dto.page import Page, PageRequest
from src.core.db.models.course_material import CourseMaterial
from src.core.db.repositories.base import BaseRepository


class CourseMaterialRepository(BaseRepository[CourseMaterial]):
    model = CourseMaterial

    async def page_for_course(self, course_id: UUID, page: PageRequest) -> Page[CourseMaterial]:
        query = (
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id)
            .options(selectinload(CourseMaterial.files))
        )
        return await self._page(query, page, CourseMaterial.id.desc())

    async def get_with_files(self, material_id: UUID) -> CourseMaterial | None:
        """Материал с файлами; уже загруженный в сессию объект перечитывается из БД."""
        query = (
            select(CourseMaterial)
            .where(CourseMaterial.id == material_id)
            .options(selectinload(CourseMaterial.files))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def touch(self, material_id: UUID) -> None:
        """Отмечает, что материал изменился, хотя его собственные поля прежние."""
        query = (
            update(CourseMaterial)
            .where(CourseMaterial.id == material_id)
            .values(updated_at=func.now())
        )
        await self._session.execute(query)
