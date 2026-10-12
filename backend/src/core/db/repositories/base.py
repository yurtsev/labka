from collections.abc import Callable, Collection, Sequence
from math import ceil
from typing import Any

from sqlalchemy import ColumnExpressionArgument, Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

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

    async def _present(
        self, column: InstrumentedAttribute[str | None], values: Collection[str]
    ) -> set[str]:
        """Какие из `values` уже записаны в колонку `column`."""
        if not values:
            return set()
        found = await self._session.scalars(select(column).where(column.in_(values)))
        return {value for value in found if value is not None}

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
        rows = await self._session.scalars(self._slice(query, page, order_by))
        return self._page_of(tuple(rows), page, await self._total(query))

    async def _page_rows[RowType](
        self,
        query: Select[Any],
        page: PageRequest,
        order_by: Sequence[ColumnExpressionArgument[object]],
        build: Callable[[Row[Any]], RowType],
    ) -> Page[RowType]:
        """Как `_page`, но для запроса из нескольких колонок: каждая строка собирается `build`."""
        rows = await self._session.execute(self._slice(query, page, order_by))
        return self._page_of(
            tuple(build(row) for row in rows.all()), page, await self._total(query)
        )

    async def _total(self, query: Select[Any]) -> int:
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        return total or 0

    @staticmethod
    def _slice[Q: Select[Any]](
        query: Q, page: PageRequest, order_by: Sequence[ColumnExpressionArgument[object]]
    ) -> Q:
        return (
            query.order_by(*order_by).offset((page.page - 1) * page.per_page).limit(page.per_page)
        )

    @staticmethod
    def _page_of[T](items: tuple[T, ...], page: PageRequest, total: int) -> Page[T]:
        return Page(
            items=items,
            page=page.page,
            per_page=page.per_page,
            total=total,
            pages=max(1, ceil(total / page.per_page)),
        )
