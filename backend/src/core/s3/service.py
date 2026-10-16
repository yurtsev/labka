import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Collection, Sequence
from contextlib import asynccontextmanager
from urllib.parse import quote

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from src.config import cfg
from src.core.errors import AppError, ErrorReport
from src.core.s3.client import S3Client
from src.core.s3.dto import PresignedUpload, StoredObject, UploadedFile
from src.core.s3.exc import (
    S3BadResponseError,
    S3FileTooLargeError,
    S3ForeignKeyError,
    S3ObjectNotFoundError,
    S3TimeoutError,
    S3UnavailableError,
)

log = logging.getLogger(__name__)


class S3Storage:
    """Файлы в S3: браузер загружает и скачивает их сам по presigned-ссылкам."""

    def __init__(self, client: S3Client) -> None:
        self._client = client

    @staticmethod
    def check_size(file_size: int) -> None:
        """Проверяет размер файла до выдачи формы и после загрузки.

        Raises:
            S3FileTooLargeError: файл больше лимита из конфига.
        """
        if file_size > cfg.s3.max_file_size_bytes:
            raise S3FileTooLargeError({"max_bytes": cfg.s3.max_file_size_bytes})

    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        """Форма прямой загрузки в S3 с лимитом размера из конфига.

        Тип файла не ограничивается, но фиксируется: объект отдаётся с тем же типом.
        """
        post = await self._client.signer.generate_presigned_post(
            Bucket=cfg.s3.bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, cfg.s3.max_file_size_bytes],
            ],
            ExpiresIn=cfg.s3.url_ttl_seconds,
        )
        return PresignedUpload(
            key=key,
            url=str(post["url"]),
            fields={str(name): str(value) for name, value in post["fields"].items()},
        )

    async def presign_download(self, key: str, file_name: str) -> str:
        """Ссылка на скачивание; браузер сохранит файл под исходным именем."""
        url = await self._client.signer.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": cfg.s3.bucket,
                "Key": key,
                "ResponseContentDisposition": f"attachment; filename*=UTF-8''{quote(file_name)}",
            },
            ExpiresIn=cfg.s3.url_ttl_seconds,
        )
        return str(url)

    async def presign_view(self, key: str) -> str:
        """Ссылка для показа в браузере (например, аватарка в `<img>`)."""
        url = await self._client.signer.generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg.s3.bucket, "Key": key},
            ExpiresIn=cfg.s3.url_ttl_seconds,
        )
        return str(url)

    async def stat(self, key: str) -> StoredObject:
        """Размер и тип загруженного объекта.

        Raises:
            S3ObjectNotFoundError: объекта нет — браузер его не загрузил.
        """
        async with self._translate_errors(key):
            head = await self._client.api.head_object(Bucket=cfg.s3.bucket, Key=key)
        return StoredObject(
            size=int(head["ContentLength"]),
            content_type=str(head.get("ContentType") or "application/octet-stream"),
        )

    async def uploaded(self, file: UploadedFile, prefix: str) -> StoredObject:
        """Проверяет файл, который браузер загрузил по форме бэкенда, и отдаёт его размер и тип.

        Raises:
            S3ForeignKeyError: ключ выдан не для этой загрузки — не начинается с `prefix`.
            S3ObjectNotFoundError: объекта нет — браузер его не загрузил.
            S3FileTooLargeError: файл больше лимита из конфига.
        """
        if not file.key.startswith(prefix):
            raise S3ForeignKeyError
        stored = await self.stat(file.key)
        self.check_size(stored.size)
        return stored

    async def delete(self, key: str) -> None:
        """Удаляет объект; отсутствие объекта — не ошибка."""
        async with self._translate_errors(key):
            await self._client.api.delete_object(Bucket=cfg.s3.bucket, Key=key)

    async def delete_many(self, keys: Collection[str]) -> None:
        """Удаляет объекты одним запросом; отсутствие объекта — не ошибка.

        Raises:
            S3BadResponseError: хотя бы один объект S3 удалить отказался.
        """
        if not keys:
            return
        async with self._translate_errors(None):
            result = await self._client.api.delete_objects(
                Bucket=cfg.s3.bucket,
                Delete={"Objects": [{"Key": key} for key in keys], "Quiet": True},
            )
        if errors := result.get("Errors"):
            raise S3BadResponseError({"failed": len(errors)})

    @asynccontextmanager
    async def discard_on_error(
        self,
        keys: Sequence[str],
        *,
        prefix: str,
        attached: Callable[[Collection[str]], Awaitable[set[str]]],
    ) -> AsyncIterator[None]:
        """Если запрос отклонён, удаляет из S3 файлы, которые браузер успел загрузить.

        Удаляются только ключи с нужным префиксом, которые не прикреплены ни к одной записи:
        чужой или уже используемый файл так не стереть. Ошибка самой очистки не заменяет
        исходную — в лог уходит предупреждение.

        Args:
            keys: ключи, присланные клиентом.
            prefix: префикс, под которым такие ключи выдаёт бэкенд.
            attached: возвращает, какие из ключей уже прикреплены к записям.
        """
        try:
            yield
        except AppError:
            try:
                candidates = [key for key in keys if key.startswith(prefix)]
                await self.delete_many(set(candidates) - await attached(candidates))
            except AppError as exc:
                log.warning(
                    "s3.discard_failed", extra={"error": ErrorReport.from_exception(exc).to_log()}
                )
            raise

    @staticmethod
    @asynccontextmanager
    async def _translate_errors(key: str | None) -> AsyncIterator[None]:
        try:
            yield
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                raise S3ObjectNotFoundError({"key": key}) from exc
            raise S3BadResponseError({"status": status}) from exc
        except (ConnectTimeoutError, ReadTimeoutError) as exc:
            raise S3TimeoutError from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise S3UnavailableError from exc
