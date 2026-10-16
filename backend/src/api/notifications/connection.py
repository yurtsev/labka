import asyncio
from collections.abc import Mapping

from starlette.websockets import WebSocket, WebSocketDisconnect


class WebSocketConnection:
    """WebSocket для хаба: записи из разных задач идут по очереди, обрыв — `ConnectionError`."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket
        self._lock = asyncio.Lock()

    async def send_json(self, data: Mapping[str, object]) -> None:
        async with self._lock:
            try:
                await self._websocket.send_json(data)
            except WebSocketDisconnect as exc:
                raise ConnectionError from exc

    async def close(self, code: int) -> None:
        async with self._lock:
            try:
                await self._websocket.close(code)
            except WebSocketDisconnect as exc:
                raise ConnectionError from exc
