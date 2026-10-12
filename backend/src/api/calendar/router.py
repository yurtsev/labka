from datetime import date
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query

from src.api.calendar.schemas import CalendarResponse
from src.api.calendar.service import CalendarService
from src.core.schedule.enums import CalendarView
from src.core.security.dto import CurrentUser
from src.core.utils.moscow_time import now_moscow

router = APIRouter(prefix="/calendar", tags=["calendar"], route_class=DishkaRoute)


@router.get("")
async def get_calendar(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CalendarService],
    view: CalendarView = CalendarView.WEEK,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> CalendarResponse:
    """Календарь на день, неделю или месяц; без даты — период с сегодняшним днём (МСК)."""
    calendar = await service.get(current_user, view, day or now_moscow().date())
    return CalendarResponse.model_validate(calendar, from_attributes=True)
