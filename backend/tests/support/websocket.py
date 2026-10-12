import asyncio
import json
from collections.abc import MutableMapping
from types import TracebackType
from typing import Any, Self

from fastapi import FastAPI
from httpx import AsyncClient


class WebSocketClosedError(Exception):
    """Сервер закрыл соединение; `code` — код закрытия."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


class WebSocketSession:
    """Клиент WebSocket поверх ASGI в том же цикле событий, что и база данных теста.

    Cookie берутся у `httpx`-клиента, то есть подключается тот, кто сейчас в нём вошёл.
    """

    def __init__(
        self,
        app: FastAPI,
        client: AsyncClient,
        path: str = "/api/ws",
        origin: str | None = None,
    ) -> None:
        self._app = app
        cookies = "; ".join(f"{c.name}={c.value}" for c in client.cookies.jar)
        headers = [(b"host", b"testserver"), (b"cookie", cookies.encode())]
        if origin is not None:
            headers.append((b"origin", origin.encode()))
        self._scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "subprotocols": [],
        }
        self._incoming: asyncio.Queue[dict] = asyncio.Queue()
        self._outgoing: asyncio.Queue[dict] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> Self:
        await self._incoming.put({"type": "websocket.connect"})
        self._task = asyncio.create_task(self._app(self._scope, self._incoming.get, self._send))
        message = await self._next()
        if message["type"] == "websocket.close":
            raise WebSocketClosedError(message.get("code", 1000))
        assert message["type"] == "websocket.accept", message
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._incoming.put({"type": "websocket.disconnect", "code": 1000})
        if self._task is not None:
            await asyncio.wait_for(self._task, 5)

    async def _send(self, message: MutableMapping[str, Any]) -> None:
        await self._outgoing.put(dict(message))

    async def receive_json(self, timeout: float = 5) -> dict:
        """Следующее сообщение сервера; закрытие сервером — `WebSocketClosedError`."""
        message = await self._next(timeout)
        if message["type"] == "websocket.close":
            raise WebSocketClosedError(message.get("code", 1000))
        assert message["type"] == "websocket.send", message
        data: dict = json.loads(message["text"])
        return data

    async def expect_silence(self, timeout: float = 0.5) -> None:
        """Проверяет, что за `timeout` секунд сервер ничего не прислал."""
        try:
            message = await self._next(timeout)
        except TimeoutError:
            return
        raise AssertionError(f"неожиданное сообщение: {message}")

    async def _next(self, timeout: float = 5) -> dict:
        return await asyncio.wait_for(self._outgoing.get(), timeout)
