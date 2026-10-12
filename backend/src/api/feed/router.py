from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.api.feed.schemas import FeedEntryResponse
from src.api.feed.service import FeedService
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.db.enums import AssignmentType
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/courses/{course_id}/feed", tags=["feed"], route_class=DishkaRoute)


@router.get("")
async def course_feed(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[FeedService],
    type: AssignmentType | None = None,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[FeedEntryResponse]:
    feed = await service.feed(current_user, course_id, type, PageRequest(page, per_page))
    return PageResponse[FeedEntryResponse].model_validate(feed, from_attributes=True)
