from httpx import AsyncClient, Response

from src.core.s3.exc import S3UnavailableError
from src.core.s3.service import S3Storage


async def upload_to_s3(form: dict[str, object], content: bytes, content_type: str) -> Response:
    """Загружает файл в S3 так, как это сделает браузер: multipart POST по форме бэкенда."""
    fields = form["fields"]
    assert isinstance(fields, dict)
    async with AsyncClient() as s3:
        return await s3.post(
            str(form["url"]),
            data=fields,
            files={"file": ("file", content, content_type)},
        )


async def download(url: str) -> Response:
    async with AsyncClient() as s3:
        return await s3.get(url)


async def s3_unavailable(self: S3Storage, *_: object) -> None:
    """Подмена `S3Storage.delete` и `S3Storage.delete_many`: хранилище не отвечает."""
    raise S3UnavailableError
