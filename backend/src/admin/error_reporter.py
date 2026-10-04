import logging
from http import HTTPStatus

from src.core.errors import DomainError, ErrorReport
from src.core.metrics import app_errors_total

log = logging.getLogger(__name__)


class AdminErrorReporter(logging.Filter):
    """Ошибки форм и действий админки — в общий формат лога и в метрику `app_errors_total`.

    sqladmin ловит любое исключение из `insert_model`/`update_model`/`delete_model`,
    показывает его текст в форме и пишет `logger.exception`. Другой точки перехвата у него
    нет, поэтому фильтр на его логгере заменяет эту запись своей: ожидаемый отказ
    (`DomainError`) — `info` без стектрейса, остальное — `error` со стектрейсом.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        exc = record.exc_info[1] if record.exc_info else None
        if exc is None:
            return True
        expected = isinstance(exc, DomainError)
        status = HTTPStatus.BAD_REQUEST if expected else HTTPStatus.INTERNAL_SERVER_ERROR
        report = ErrorReport.from_exception(exc)
        log.log(
            logging.INFO if expected else logging.ERROR,
            "admin.error",
            exc_info=None if expected else exc,
            extra={"error": {**report.to_log(), "status": status.value}},
        )
        app_errors_total.labels(
            layer=report.layer.value,
            code=report.code,
            status=status.value,
            untranslated=report.untranslated,
        ).inc()
        return False
