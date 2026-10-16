from src.core.errors import (
    CoreError,
    IntegrationBadResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


class S3FileTooLargeError(CoreError):
    code = "s3.file_too_large"
    message = "Файл больше допустимого размера"


class S3ForeignKeyError(CoreError):
    code = "s3.foreign_key"
    message = "Ключ файла выдан для другой загрузки"


class S3ObjectNotFoundError(CoreError):
    code = "s3.object_not_found"
    message = "Файл не найден в хранилище"


class S3UnavailableError(IntegrationUnavailableError):
    code = "s3.unavailable"
    message = "Файловое хранилище недоступно"


class S3TimeoutError(IntegrationTimeoutError):
    code = "s3.timeout"
    message = "Файловое хранилище не ответило вовремя"


class S3BadResponseError(IntegrationBadResponseError):
    code = "s3.bad_response"
    message = "Файловое хранилище вернуло ошибку"
