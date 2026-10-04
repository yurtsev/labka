from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Self

import aioboto3
from botocore.config import Config as BotoConfig
from types_aiobotocore_s3 import S3Client as S3ApiClient

from src.config import cfg


class S3Client:
    """Подключение к S3: клиент для запросов из бэкенда и клиент для подписи ссылок.

    Ссылки подписываются на публичный адрес: подпись включает хост, а браузер ходит
    в S3 не по тому адресу, что бэкенд внутри Docker.
    """

    def __init__(self, api: S3ApiClient, signer: S3ApiClient) -> None:
        self.api = api
        self.signer = signer

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator[Self]:
        """Открывает оба клиента на время жизни приложения."""
        settings = cfg.s3
        session = aioboto3.Session(
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            region_name=settings.region,
        )
        boto_config = BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=settings.timeout_seconds,
            read_timeout=settings.timeout_seconds,
            retries={"max_attempts": 1},
        )
        async with AsyncExitStack() as stack:
            api: S3ApiClient = await stack.enter_async_context(
                session.client("s3", endpoint_url=settings.endpoint_url, config=boto_config)
            )
            signer: S3ApiClient = await stack.enter_async_context(
                session.client(
                    "s3",
                    endpoint_url=settings.public_endpoint_url or settings.endpoint_url,
                    config=boto_config,
                )
            )
            yield cls(api, signer)
