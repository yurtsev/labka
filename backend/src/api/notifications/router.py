from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.api.notifications.schemas import ReadAllResponse, UnreadCountResponse
from src.api.notifications.service import NotificationsService
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.api.schemas import NotificationResponse
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/notifications", tags=["notifications"], route_class=DishkaRoute)


@router.get("")
async def list_notifications(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[NotificationsService],
    unread: bool = False,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[NotificationResponse]:
    found = await service.list_notifications(current_user, unread, PageRequest(page, per_page))
    return PageResponse[NotificationResponse].model_validate(found, from_attributes=True)


@router.get("/unread-count")
async def get_unread_count(
    current_user: FromDishka[CurrentUser], service: FromDishka[NotificationsService]
) -> UnreadCountResponse:
    return UnreadCountResponse(unread_count=await service.unread_count(current_user))


@router.post("/read-all")
async def read_all_notifications(
    current_user: FromDishka[CurrentUser], service: FromDishka[NotificationsService]
) -> ReadAllResponse:
    result = await service.mark_all_read(current_user)
    return ReadAllResponse.model_validate(result, from_attributes=True)


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[NotificationsService],
) -> NotificationResponse:
    notification = await service.mark_read(current_user, notification_id)
    return NotificationResponse.model_validate(notification, from_attributes=True)
