from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.api.profile.schemas import (
    AvatarSetRequest,
    AvatarUploadStartRequest,
    ProfileResponse,
    UploadFormResponse,
)
from src.api.profile.service import ProfileService
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/profile", tags=["profile"], route_class=DishkaRoute)


@router.get("")
async def get_profile(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ProfileService],
) -> ProfileResponse:
    profile = await service.get_profile(current_user)
    return ProfileResponse.model_validate(profile, from_attributes=True)


@router.post("/avatar/uploads")
async def start_avatar_upload(
    body: AvatarUploadStartRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ProfileService],
) -> UploadFormResponse:
    form = await service.start_avatar_upload(current_user, body.content_type, body.file_size)
    return UploadFormResponse.model_validate(form, from_attributes=True)


@router.put("/avatar")
async def set_avatar(
    body: AvatarSetRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ProfileService],
) -> ProfileResponse:
    profile = await service.set_avatar(current_user, body.key)
    return ProfileResponse.model_validate(profile, from_attributes=True)


@router.delete("/avatar")
async def remove_avatar(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ProfileService],
) -> ProfileResponse:
    profile = await service.remove_avatar(current_user)
    return ProfileResponse.model_validate(profile, from_attributes=True)
