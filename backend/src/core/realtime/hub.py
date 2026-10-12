import logging
from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

log = logging.getLogger(__name__)


class Connection(Protocol):
    """Открытое соединение с клиентом, в которое можно писать и которое можно закрыть."""

    async def send_json(self, data: Mapping[str, object]) -> None: ...

    async def close(self, code: int) -> None: ...


class RealtimeHub:
    """Открытые WebSocket-соединения этого процесса: кому из пользователей куда писать.

    Хранит соединения в памяти. У человека их может быть несколько (вкладки, устройства),
    у каждого — своя сессия. При нескольких воркерах у каждого свой хаб, а события приходят
    всем через PostgreSQL, поэтому каждый воркер пишет только в свои соединения.
    """

    def __init__(self) -> None:
        self._by_user: dict[UUID, set[Connection]] = {}
        self._by_session: dict[UUID, set[Connection]] = {}
        self._owners: dict[Connection, tuple[UUID, UUID]] = {}

    def register(self, user_id: UUID, session_id: UUID, connection: Connection) -> None:
        self._by_user.setdefault(user_id, set()).add(connection)
        self._by_session.setdefault(session_id, set()).add(connection)
        self._owners[connection] = (user_id, session_id)

    def unregister(self, connection: Connection) -> None:
        owner = self._owners.pop(connection, None)
        if owner is None:
            return
        user_id, session_id = owner
        for index, key in ((self._by_user, user_id), (self._by_session, session_id)):
            connections = index.get(key)
            if connections is not None:
                connections.discard(connection)
                if not connections:
                    del index[key]

    def online_users(self) -> set[UUID]:
        """Пользователи, у которых сейчас есть открытые соединения."""
        return set(self._by_user)

    def has_user(self, user_id: UUID) -> bool:
        return user_id in self._by_user

    async def send_to_user(self, user_id: UUID, message: Mapping[str, object]) -> int:
        """Пишет во все соединения пользователя; возвращает, в сколько удалось записать.

        Соединение, в которое записать не вышло, считается закрытым и убирается.
        """
        sent = 0
        for connection in list(self._by_user.get(user_id, ())):
            if await self._send(connection, message):
                sent += 1
        return sent

    async def broadcast(self, message: Mapping[str, object]) -> None:
        """Пишет во все открытые соединения."""
        for connection in list(self._owners):
            await self._send(connection, message)

    async def close_session(self, session_id: UUID, code: int) -> None:
        """Закрывает соединения отозванной сессии."""
        for connection in list(self._by_session.get(session_id, ())):
            await self._close(connection, code)

    async def close_all(self, code: int) -> None:
        """Закрывает все соединения — при остановке приложения."""
        for connection in list(self._owners):
            await self._close(connection, code)

    async def _send(self, connection: Connection, message: Mapping[str, object]) -> bool:
        try:
            await connection.send_json(message)
        except RuntimeError, OSError:
            log.info("realtime.connection_dropped")
            self.unregister(connection)
            return False
        return True

    async def _close(self, connection: Connection, code: int) -> None:
        self.unregister(connection)
        try:
            await connection.close(code)
        except RuntimeError, OSError:
            log.info("realtime.connection_already_closed")
