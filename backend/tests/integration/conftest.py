from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session")
async def app() -> AsyncIterator[FastAPI]:
    # Импорт внутри фикстуры намеренный: src.main создаёт engine и `cfg` при импорте,
    # а адрес тестового PostgreSQL известен только после pytest_sessionstart.
    from src.main import app, container

    yield app
    await container.close()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def db(app: FastAPI) -> AsyncIterator[AsyncSession]:
    """Отдельная сессия для подготовки и проверки данных в обход API."""
    from src.core.db.db import Session

    async with Session() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def clean_database(app: FastAPI) -> AsyncIterator[None]:
    yield
    from src.core.db.db import engine
    from src.core.db.models import Base

    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
async def realtime(app: FastAPI) -> AsyncIterator[None]:
    """Слушатель PostgreSQL запущен: WebSocket получает уведомления, как в работающем сервисе."""
    from src.core.realtime.listener import PostgresListener
    from src.main import container

    listener = await container.get(PostgresListener)
    listener.start()
    await listener.wait_ready()
    yield
    await listener.stop()
