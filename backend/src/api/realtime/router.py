import asyncio

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, WebSocket

from src.api.realtime.connection import WebSocketConnection
from src.api.realtime.schemas import PingMessage, ReadyMessage
from src.api.realtime.service import RealtimeService
from src.config import cfg
from src.core.realtime.hub import RealtimeHub
from src.core.security.enums import AuthCookie
from src.core.security.exc import NotAuthenticatedError

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
@inject
async def notifications_socket(
    websocket: WebSocket,
    service: FromDishka[RealtimeService],
    hub: FromDishka[RealtimeHub],
) -> None:
    """Уведомления в реальном времени.

    Аутентификация — по cookie, как у REST. Закрытие: 4401 — не вошёл или сессия отозвана,
    4403 — запрос с чужого сайта. Сервер присылает `ready`, затем `notification`, `ping` и
    `resync`; сообщения клиента игнорируются.
    """
    await websocket.accept()
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in cfg.cors.origins:
        await websocket.close(4403)
        return
    try:
        user = await service.authenticate(websocket.cookies.get(AuthCookie.ACCESS_TOKEN))
    except NotAuthenticatedError:
        await websocket.close(4401)
        return
    connection = WebSocketConnection(websocket)
    hub.register(user.user_id, user.session_id, connection)
    try:
        unread = await service.unread_count(user.user_id)
        await connection.send_json(ReadyMessage(unread_count=unread).model_dump(mode="json"))
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), cfg.notifications.websocket_ping_seconds
                )
            except TimeoutError:
                await connection.send_json(PingMessage().model_dump(mode="json"))
                continue
            if message["type"] == "websocket.disconnect":
                break
    except ConnectionError:
        pass
    finally:
        hub.unregister(connection)
