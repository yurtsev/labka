import asyncio
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket

from src.api.notifications.connection import WebSocketConnection
from src.api.notifications.schemas import (
    NotificationResponse,
    PingMessage,
    ReadAllResponse,
    ReadyMessage,
    UnreadCountResponse,
)
from src.api.notifications.service import NotificationsService, RealtimeService
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.realtime.hub import RealtimeHub
from src.core.security.dto import CurrentUser
from src.core.security.enums import AuthCookie
from src.core.security.exc import NotAuthenticatedError

# Без общего префикса: WebSocket живёт на `/api/ws`, остальное — под `/api/notifications`.
router = APIRouter(tags=["notifications"], route_class=DishkaRoute)


@router.get("/notifications")
async def list_notifications(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[NotificationsService],
    unread: bool = False,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[NotificationResponse]:
    found = await service.list_notifications(current_user, unread, PageRequest(page, per_page))
    return PageResponse[NotificationResponse].model_validate(found, from_attributes=True)


@router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: FromDishka[CurrentUser], service: FromDishka[NotificationsService]
) -> UnreadCountResponse:
    return UnreadCountResponse(unread_count=await service.unread_count(current_user))


@router.post("/notifications/read-all")
async def read_all_notifications(
    current_user: FromDishka[CurrentUser], service: FromDishka[NotificationsService]
) -> ReadAllResponse:
    result = await service.mark_all_read(current_user)
    return ReadAllResponse.model_validate(result, from_attributes=True)


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[NotificationsService],
) -> NotificationResponse:
    notification = await service.mark_read(current_user, notification_id)
    return NotificationResponse.model_validate(notification, from_attributes=True)


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
