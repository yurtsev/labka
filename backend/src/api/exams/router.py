from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.exams.schemas import ExamRequest, ExamResponse, ExamsResponse
from src.api.exams.service import ExamService
from src.api.exams.utils import exam_fields
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/courses/{course_id}/exams", tags=["exams"], route_class=DishkaRoute)


@router.get("")
async def list_exams(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ExamService],
) -> ExamsResponse:
    exams = await service.list_exams(current_user, course_id)
    return ExamsResponse.model_validate({"items": exams}, from_attributes=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_exam(
    course_id: UUID,
    body: ExamRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ExamService],
) -> ExamResponse:
    exam = await service.create(current_user, course_id, exam_fields(body))
    return ExamResponse.model_validate(exam, from_attributes=True)


@router.put("/{exam_id}")
async def update_exam(
    course_id: UUID,
    exam_id: UUID,
    body: ExamRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ExamService],
) -> ExamResponse:
    exam = await service.update(current_user, course_id, exam_id, exam_fields(body))
    return ExamResponse.model_validate(exam, from_attributes=True)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    course_id: UUID,
    exam_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ExamService],
) -> None:
    await service.delete(current_user, course_id, exam_id)
