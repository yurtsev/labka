from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.core.s3.client import S3Client
from src.core.s3.service import S3Storage


class S3Provider(Provider):
    s3_storage = provide(S3Storage, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def get_client(self) -> AsyncIterator[S3Client]:
        async with S3Client.connect() as client:
            yield client
