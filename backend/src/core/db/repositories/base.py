from math import ceil

from sqlalchemy import ColumnExpressionArgument, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.dto.page import Page, PageRequest
from src.core.db.models.base import Base


class BaseRepository[ModelType: Base]:
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: object) -> ModelType | None:
        return await self._session.get(self.model, id)

    def add(self, obj: ModelType) -> None:
        self._session.add(obj)

    async def delete(self, obj: ModelType) -> None:
        await self._session.delete(obj)

    async def _page(
        self,
        query: Select[tuple[ModelType]],
        page: PageRequest,
        *order_by: ColumnExpressionArgument[object],
    ) -> Page[ModelType]:
        """Страница выборки и общее число записей по тому же запросу.

        `order_by` должен давать однозначный порядок (последним — уникальная колонка),
        иначе записи на границе страниц могут повторяться или теряться.
        """
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        total = total or 0
        rows = await self._session.scalars(
            query.order_by(*order_by).offset((page.page - 1) * page.per_page).limit(page.per_page)
        )
        return Page(
            items=tuple(rows),
            page=page.page,
            per_page=page.per_page,
            total=total,
            pages=max(1, ceil(total / page.per_page)),
        )
