from typing import Any

from sqlalchemy.engine import Dialect, ExceptionContext
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.pool import ConnectionPoolEntry

from src.core.db.exc import DatabaseUnavailableError, IntegrityViolationError


class DatabaseErrorTranslator:
    """Переводит ошибки драйвера в ошибки DB-слоя на уровне engine.

    Благодаря этому SQLAlchemy/asyncpg-исключения не протекают выше
    `src/core/db/`, и репозиториям не нужен `try/except` вокруг каждого запроса.
    Слушатели регистрируются в `src/core/db/db.py`.
    """

    @staticmethod
    def on_connect(
        dialect: Dialect,
        conn_rec: ConnectionPoolEntry,
        cargs: tuple[Any, ...],
        cparams: dict[str, Any],
    ) -> Any:
        """Слушатель `do_connect`: отказ подключения asyncpg не проходит через `handle_error`."""
        try:
            return dialect.connect(*cargs, **cparams)
        except (OSError, dialect.loaded_dbapi.Error) as exc:
            raise DatabaseUnavailableError from exc

    @staticmethod
    def on_error(context: ExceptionContext) -> BaseException | None:
        """Слушатель `handle_error` (с `retval=True`): возвращённое исключение заменяет исходное."""
        error = context.sqlalchemy_exception
        if isinstance(error, IntegrityError):
            constraint = getattr(context.original_exception.__cause__, "constraint_name", None)
            return IntegrityViolationError(constraint)
        if context.is_disconnect or isinstance(error, OperationalError | InterfaceError):
            return DatabaseUnavailableError()
        return None
