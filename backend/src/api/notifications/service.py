from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.api.exc.notifications import NotificationNotFoundError
from src.api.notifications.dto import ReadAll
from src.core.db.dto.page import Page, PageRequest
from src.core.db.uow import UnitOfWork
from src.core.notifications.dto import NotificationView
from src.core.notifications.service import NotificationService
from src.core.security.dto import CurrentUser
from src.core.security.service import SecurityService, SessionAuthenticator


class NotificationsService:
    """Список уведомлений пользователя, счётчик и отметки «прочитано»."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_notifications(
        self, user: CurrentUser, unread_only: bool, page: PageRequest
    ) -> Page[NotificationView]:
        """Уведомления пользователя, новые первыми."""
        found = await self._uow.notifications.page_for_user(user.user_id, unread_only, page)
        return found.map(NotificationService.views(found.items))

    async def unread_count(self, user: CurrentUser) -> int:
        return await self._uow.notifications.count_unread(user.user_id)

    async def mark_read(self, user: CurrentUser, notification_id: UUID) -> NotificationView:
        """Отмечает уведомление прочитанным; повторная отметка ничего не меняет.

        Raises:
            NotificationNotFoundError: уведомления нет или оно чужое.
        """
        if not await self._uow.notifications.mark_read(user.user_id, notification_id):
            raise NotificationNotFoundError({"notification_id": str(notification_id)})
        await self._uow.commit()
        [notification] = await self._uow.notifications.get_many([notification_id])
        return NotificationService.view(notification)

    async def mark_all_read(self, user: CurrentUser) -> ReadAll:
        """Отмечает прочитанными все уведомления пользователя."""
        marked = await self._uow.notifications.mark_all_read(user.user_id)
        await self._uow.commit()
        return ReadAll(
            marked=marked, unread_count=await self._uow.notifications.count_unread(user.user_id)
        )


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
