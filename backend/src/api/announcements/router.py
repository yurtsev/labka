from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.announcements.schemas import AnnouncementRequest, AnnouncementResponse
from src.api.announcements.service import AnnouncementService
from src.core.security.dto import CurrentUser

router = APIRouter(
    prefix="/courses/{course_id}/announcements", tags=["announcements"], route_class=DishkaRoute
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_announcement(
    course_id: UUID,
    body: AnnouncementRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AnnouncementService],
) -> AnnouncementResponse:
    announcement = await service.create(current_user, course_id, body.text)
    return AnnouncementResponse.model_validate(announcement, from_attributes=True)


@router.put("/{announcement_id}")
async def update_announcement(
    course_id: UUID,
    announcement_id: UUID,
    body: AnnouncementRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AnnouncementService],
) -> AnnouncementResponse:
    announcement = await service.update(current_user, course_id, announcement_id, body.text)
    return AnnouncementResponse.model_validate(announcement, from_attributes=True)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    course_id: UUID,
    announcement_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AnnouncementService],
) -> None:
    await service.delete(current_user, course_id, announcement_id)
