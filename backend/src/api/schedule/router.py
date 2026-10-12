from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.schedule.schemas import (
    CourseScheduleResponse,
    ExtraRequest,
    ExtraResponse,
    RuleRequest,
    RuleResponse,
    SlotsResponse,
)
from src.api.schedule.service import ScheduleCourseService
from src.api.schedule.utils import extra_fields, rule_fields
from src.core.security.dto import CurrentUser

router = APIRouter(tags=["schedule"], route_class=DishkaRoute)


@router.get("/schedule/slots")
async def list_slots(
    current_user: FromDishka[CurrentUser], service: FromDishka[ScheduleCourseService]
) -> SlotsResponse:
    return SlotsResponse.model_validate(service.slots(), from_attributes=True)


@router.get("/courses/{course_id}/schedule")
async def get_course_schedule(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> CourseScheduleResponse:
    schedule = await service.get(current_user, course_id)
    return CourseScheduleResponse.model_validate(schedule, from_attributes=True)


@router.post("/courses/{course_id}/schedule/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    course_id: UUID,
    body: RuleRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> RuleResponse:
    rule = await service.create_rule(current_user, course_id, rule_fields(body))
    return RuleResponse.model_validate(rule, from_attributes=True)


@router.put("/courses/{course_id}/schedule/rules/{rule_id}")
async def update_rule(
    course_id: UUID,
    rule_id: UUID,
    body: RuleRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> RuleResponse:
    rule = await service.update_rule(current_user, course_id, rule_id, rule_fields(body))
    return RuleResponse.model_validate(rule, from_attributes=True)


@router.delete(
    "/courses/{course_id}/schedule/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_rule(
    course_id: UUID,
    rule_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> None:
    await service.delete_rule(current_user, course_id, rule_id)


@router.post("/courses/{course_id}/schedule/extras", status_code=status.HTTP_201_CREATED)
async def create_extra(
    course_id: UUID,
    body: ExtraRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> ExtraResponse:
    extra = await service.create_extra(current_user, course_id, extra_fields(body))
    return ExtraResponse.model_validate(extra, from_attributes=True)


@router.put("/courses/{course_id}/schedule/extras/{extra_id}")
async def update_extra(
    course_id: UUID,
    extra_id: UUID,
    body: ExtraRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> ExtraResponse:
    extra = await service.update_extra(current_user, course_id, extra_id, extra_fields(body))
    return ExtraResponse.model_validate(extra, from_attributes=True)


@router.delete(
    "/courses/{course_id}/schedule/extras/{extra_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_extra(
    course_id: UUID,
    extra_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ScheduleCourseService],
) -> None:
    await service.delete_extra(current_user, course_id, extra_id)
