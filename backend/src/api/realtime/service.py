from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.db.uow import UnitOfWork
from src.core.security.dto import CurrentUser
from src.core.security.service import SecurityService, SessionAuthenticator


class RealtimeService:
    """Проверка подключения к WebSocket и данные для первого сообщения."""

    def __init__(self, security: SecurityService, sessionmaker: async_sessionmaker) -> None:
        self._security = security
        self._sessionmaker = sessionmaker

    async def authenticate(self, access_token: str | None) -> CurrentUser:
        """Пользователь по access-токену из cookie: сессия не отозвана, аккаунт активен.

        Raises:
            NotAuthenticatedError: токена нет или проверка не прошла.
        """
        async with self._sessionmaker() as session:
            return await SessionAuthenticator(UnitOfWork(session), self._security).authenticate(
                access_token
            )

    async def unread_count(self, user_id: UUID) -> int:
        async with self._sessionmaker() as session:
            return await UnitOfWork(session).notifications.count_unread(user_id)
