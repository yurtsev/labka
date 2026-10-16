from datetime import date
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from src.api.calendar.dto import TaskFields
from src.api.calendar.schemas import (
    CalendarResponse,
    TaskDoneRequest,
    TaskRequest,
    TaskResponse,
    TasksResponse,
)
from src.api.calendar.service import CalendarService, PersonalTaskService
from src.core.schedule.enums import CalendarView
from src.core.security.dto import CurrentUser
from src.core.utils.moscow_time import now_moscow

# Без общего префикса: календарь — `/api/calendar`, личные задачи в нём — `/api/personal-tasks`.
router = APIRouter(tags=["calendar"], route_class=DishkaRoute)


@router.get("/calendar")
async def get_calendar(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CalendarService],
    view: CalendarView = CalendarView.WEEK,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> CalendarResponse:
    """Календарь на день, неделю или месяц; без даты — период с сегодняшним днём (МСК)."""
    calendar = await service.get(current_user, view, day or now_moscow().date())
    return CalendarResponse.model_validate(calendar, from_attributes=True)


@router.get("/personal-tasks")
async def list_tasks(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[PersonalTaskService],
    first: Annotated[date, Query(alias="from")],
    last: Annotated[date, Query(alias="to")],
) -> TasksResponse:
    tasks = await service.list_between(current_user, first, last)
    return TasksResponse.model_validate({"items": tasks}, from_attributes=True)


@router.post("/personal-tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[PersonalTaskService],
) -> TaskResponse:
    task = await service.create(current_user, TaskFields(body.title, body.due_date, body.due_time))
    return TaskResponse.model_validate(task, from_attributes=True)


@router.put("/personal-tasks/{task_id}")
async def update_task(
    task_id: UUID,
    body: TaskRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[PersonalTaskService],
) -> TaskResponse:
    task = await service.update(
        current_user, task_id, TaskFields(body.title, body.due_date, body.due_time)
    )
    return TaskResponse.model_validate(task, from_attributes=True)


@router.patch("/personal-tasks/{task_id}/done")
async def set_task_done(
    task_id: UUID,
    body: TaskDoneRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[PersonalTaskService],
) -> TaskResponse:
    task = await service.set_done(current_user, task_id, body.is_done)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.delete("/personal-tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[PersonalTaskService],
) -> None:
    await service.delete(current_user, task_id)
