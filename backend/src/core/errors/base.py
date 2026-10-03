from collections.abc import Mapping
from typing import ClassVar

from src.core.errors.enums import ErrorLayer


class AppError(Exception):
    """Базовая ошибка приложения.

    Конкретная ошибка — подкласс одной из категорий ниже со своими `code`
    (стабильный машинный код `<domain|system>.<reason>`) и `message`.
    Динамика передаётся только через `context`: безопасные поля (ID, enum,
    количества), которые попадают в лог и, для доменных ошибок, в ответ.
    """

    code: ClassVar[str] = "app.error"
    message: ClassVar[str] = "Ошибка приложения"
    layer: ClassVar[ErrorLayer | None] = None

    def __init__(self, context: Mapping[str, object] | None = None) -> None:
        super().__init__(self.message)
        self.context: dict[str, object] = dict(context or {})


class DomainError(AppError):
    """Ожидаемый отказ по бизнес-правилу. Объявляется только в `src/api/exc/<domain>.py`."""

    layer = ErrorLayer.DOMAIN


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class RuleViolationError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class CoreError(AppError):
    """Смысловая ошибка core-подсистемы.

    Не имеет HTTP-интерпретации: домен-вызывающий обязан перевести её в свою
    `DomainError`. Непереведённая ошибка отдаётся как 500 и помечается в
    мониторинге как `untranslated`.
    """

    layer = ErrorLayer.CORE


class IntegrationError(AppError):
    """Отказ внешней системы. Проходит до API-обработчика без перевода."""

    layer = ErrorLayer.INTEGRATION


class IntegrationUnavailableError(IntegrationError):
    pass


class IntegrationTimeoutError(IntegrationError):
    pass


class IntegrationBadResponseError(IntegrationError):
    pass


class PersistenceError(AppError):
    layer = ErrorLayer.DB


class PersistenceUnavailableError(PersistenceError):
    """БД недоступна. Проходит до API-обработчика без перевода."""


class PersistenceConflictError(PersistenceError):
    """Нарушено ограничение целостности. Как и `CoreError`, требует перевода доменом."""


class InternalError(AppError):
    """Нарушен инвариант кода. Слой определяется по месту возникновения."""

    code = "internal_error"
    message = "Внутренняя ошибка сервера"
