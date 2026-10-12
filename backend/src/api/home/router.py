from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.api.home.schemas import HomeResponse
from src.api.home.service import HomeService
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/home", tags=["home"], route_class=DishkaRoute)


@router.get("")
async def get_home(
    current_user: FromDishka[CurrentUser], service: FromDishka[HomeService]
) -> HomeResponse:
    """Главная. Студент: ближайший дедлайн, следующие дедлайны, занятия, курсы с числом несданных
    заданий. Преподаватель: число работ на проверке, занятия, курсы с числом работ на проверке."""
    home = await service.get(current_user)
    return HomeResponse.model_validate(home, from_attributes=True)
