from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    """Номер страницы с 1 и размер страницы."""

    page: int
    per_page: int


@dataclass(frozen=True)
class Page[T]:
    items: tuple[T, ...]
    page: int
    per_page: int
    # Всего записей и страниц по запросу; пустой результат — одна пустая страница.
    total: int
    pages: int

    def map[R](self, items: tuple[R, ...]) -> Page[R]:
        """Та же страница с другими элементами — например, ORM-модели → DTO."""
        return Page(
            items=items, page=self.page, per_page=self.per_page, total=self.total, pages=self.pages
        )
