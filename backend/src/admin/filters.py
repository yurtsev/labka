from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Self

from sqlalchemy import Select, false
from starlette.requests import Request

type Apply = Callable[[Select[Any], str], Select[Any]]
type RunQuery = Callable[[Select[Any]], Awaitable[Sequence[Any]]]


class LookupFilter:
    """Фильтр списка sqladmin по одному значению из выпадающего перечня, подписи по-русски.

    Значения перечня — статический список пар `(значение, подпись)` или запрос, возвращающий
    такие пары. `apply` добавляет условие в запрос списка.
    """

    has_operator = False
    template = "sqladmin/filters/lookup_filter.html"
    # Фильтр без значения по умолчанию: пока значение не выбрано, список не сужается.
    default_value: Any = None

    def __init__(
        self,
        title: str,
        parameter_name: str,
        apply: Apply,
        *,
        options: Sequence[tuple[str, str]] = (),
        options_query: Select[Any] | None = None,
    ) -> None:
        self.title = title
        self.parameter_name = parameter_name
        self._apply = apply
        self._options = options
        self._options_query = options_query

    async def lookups(
        self, request: Request, model: Any, run_query: RunQuery
    ) -> list[tuple[str, str]]:
        found = list(self._options)
        if self._options_query is not None:
            found += [(str(key), str(label)) for key, label in await run_query(self._options_query)]
        return [("__all", "Все"), *found]

    async def get_filtered_query(self, query: Select[Any], value: Any, model: Any) -> Select[Any]:
        if value in (None, "", "__all"):
            return query
        try:
            return self._apply(query, str(value))
        except ValueError:
            # Подделанное значение в адресе (например, не UUID): ничего не показываем.
            return query.where(false())

    @classmethod
    def yes_no(cls, title: str, parameter_name: str, apply: Apply) -> Self:
        """Фильтр «да / нет» со значениями `true` и `false`."""
        return cls(title, parameter_name, apply, options=[("true", "Да"), ("false", "Нет")])
