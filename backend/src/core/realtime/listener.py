import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping

import asyncpg

from src.core.errors import AppError, ErrorReport

log = logging.getLogger(__name__)

type Handler = Callable[[str], Awaitable[None]]


class PostgresListener:
    """Слушает каналы PostgreSQL (`LISTEN`) на отдельном соединении.

    NOTIFY из триггеров приходит только после коммита транзакции, поэтому подписчик никогда
    не видит данные, которых ещё нет в БД. При обрыве соединение восстанавливается с
    нарастающей паузой, а после восстановления вызывается `on_reconnect`: за время обрыва
    события могли пропасть, и клиентам нужно перечитать данные.
    """

    def __init__(
        self,
        dsn: str,
        handlers: Mapping[str, Handler],
        on_reconnect: Callable[[], Awaitable[None]],
        keepalive_seconds: float = 30,
    ) -> None:
        self._dsn = dsn
        self._handlers = handlers
        self._on_reconnect = on_reconnect
        self._keepalive_seconds = keepalive_seconds
        self._task: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()

    def start(self) -> None:
        """Запускает прослушивание в фоне."""
        self._task = asyncio.create_task(self._run(), name="postgres-listener")
        self._task.add_done_callback(self._log_failure)

    async def wait_ready(self, timeout: float = 10) -> None:
        """Ждёт, пока соединение установлено и подписки оформлены.

        Raises:
            TimeoutError: соединение не удалось установить за `timeout` секунд.
        """
        await asyncio.wait_for(self._ready.wait(), timeout)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    @staticmethod
    def _log_failure(task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            log.error("realtime.listener_crashed", exc_info=task.exception())

    async def _run(self) -> None:
        pause = 1.0
        connected_before = False
        while True:
            try:
                connection = await asyncpg.connect(self._dsn)
            except (OSError, asyncpg.PostgresError) as exc:
                log.warning("realtime.listener_connect_failed", extra={"error": type(exc).__name__})
                await asyncio.sleep(pause)
                pause = min(pause * 2, 30)
                continue
            pause = 1.0
            try:
                events: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
                connection.add_termination_listener(self._enqueue_loss(events))
                for channel in self._handlers:
                    await connection.add_listener(channel, self._enqueue(events))
                if connected_before:
                    await self._on_reconnect()
                connected_before = True
                self._ready.set()
                log.info("realtime.listener_connected")
                await self._serve(connection, events)
            except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
                log.warning("realtime.listener_lost", extra={"error": type(exc).__name__})
            finally:
                self._ready.clear()
                await self._close(connection)

    @staticmethod
    def _enqueue_loss(
        events: asyncio.Queue[tuple[str, str] | None],
    ) -> Callable[[asyncpg.Connection], None]:
        def put(_connection: asyncpg.Connection) -> None:
            events.put_nowait(None)

        return put

    @staticmethod
    def _enqueue(
        events: asyncio.Queue[tuple[str, str] | None],
    ) -> Callable[[asyncpg.Connection, int, str, object], None]:
        def put(_connection: asyncpg.Connection, _pid: int, channel: str, payload: object) -> None:
            events.put_nowait((channel, str(payload)))

        return put

    async def _serve(
        self, connection: asyncpg.Connection, events: asyncio.Queue[tuple[str, str] | None]
    ) -> None:
        while True:
            try:
                event = await asyncio.wait_for(events.get(), self._keepalive_seconds)
            except TimeoutError:
                # Тихий обрыв сети иначе не заметить: запрос упадёт и запустит переподключение.
                await connection.execute("SELECT 1")
                continue
            if event is None:
                raise ConnectionError("соединение с PostgreSQL закрыто")
            channel, payload = event
            try:
                await self._handlers[channel](payload)
            except AppError as exc:
                log.warning(
                    "realtime.event_failed",
                    extra={"channel": channel, "error": ErrorReport.from_exception(exc).to_log()},
                )

    @staticmethod
    async def _close(connection: asyncpg.Connection) -> None:
        try:
            await asyncio.wait_for(connection.close(), 5)
        except OSError, TimeoutError, asyncpg.PostgresError, asyncpg.InterfaceError:
            connection.terminate()
