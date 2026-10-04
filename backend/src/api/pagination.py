from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

from src.config import cfg

type PageNumber = Annotated[int, Query(ge=1, description="Номер страницы, с 1")]
type PerPage = Annotated[int, Query(ge=1, le=cfg.pagination.max_per_page)]


class PageResponse[ItemT](BaseModel):
    """Страница списка: сколько всего записей и страниц, какая страница и её размер."""

    items: list[ItemT]
    page: int
    per_page: int
    total: int
    pages: int
