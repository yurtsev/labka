import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.api.realtime.schemas import NotificationMessage, ResyncMessage
from src.core.db.uow import UnitOfWork
from src.core.notifications.service import NotificationService
from src.core.realtime.hub import RealtimeHub

log = logging.getLogger(__name__)


class RealtimeDispatcher:
    """Превращает события PostgreSQL в сообщения для открытых WebSocket-соединений."""

    def __init__(self, hub: RealtimeHub, sessionmaker: async_sessionmaker) -> None:
        self._hub = hub
        self._sessionmaker = sessionmaker

    async def on_notification(self, payload: str) -> None:
        """Создано уведомление: если адресат в сети, отправляет ему уведомление и счётчик."""
        try:
            event = json.loads(payload)
            notification_id, user_id = UUID(event["id"]), UUID(event["user_id"])
        except ValueError, KeyError, TypeError:
            log.warning("realtime.bad_notification_event")
            return
        if not self._hub.has_user(user_id):
            return
        async with self._sessionmaker() as session:
            uow = UnitOfWork(session)
            found = await uow.notifications.get_many([notification_id])
            unread = await uow.notifications.count_unread(user_id)
        if not found:
            return
        message = NotificationMessage.model_validate(
            {"notification": NotificationService.view(found[0]), "unread_count": unread},
            from_attributes=True,
        )
        await self._hub.send_to_user(user_id, message.model_dump(mode="json"))

    async def on_session_revoked(self, payload: str) -> None:
        """Сессия отозвана (выход, смена пароля, блокировка): закрывает её соединения."""
        try:
            session_id = UUID(payload)
        except ValueError:
            log.warning("realtime.bad_session_event")
            return
        await self._hub.close_session(session_id, 4401)

    async def resync(self) -> None:
        """После обрыва связи с БД просит все соединения перечитать уведомления."""
        await self._hub.broadcast(ResyncMessage().model_dump(mode="json"))
