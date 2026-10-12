from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.final_grades.dto import FinalResult
from src.api.final_grades.schemas import (
    FinalGradeRequest,
    MyGradeResponse,
    StudentGradeResponse,
)
from src.api.final_grades.service import FinalGradeService
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.security.dto import CurrentUser

router = APIRouter(
    prefix="/courses/{course_id}/final-grades", tags=["final-grades"], route_class=DishkaRoute
)


@router.get("")
async def list_final_grades(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[FinalGradeService],
    group_id: UUID | None = None,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[StudentGradeResponse]:
    students = await service.list_students(
        current_user, course_id, group_id, PageRequest(page, per_page)
    )
    return PageResponse[StudentGradeResponse].model_validate(students, from_attributes=True)


@router.get("/me")
async def get_my_final_grade(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[FinalGradeService],
) -> MyGradeResponse:
    grade = await service.mine(current_user, course_id)
    return MyGradeResponse.model_validate(grade, from_attributes=True)


@router.put("/{student_id}")
async def set_final_grade(
    course_id: UUID,
    student_id: UUID,
    body: FinalGradeRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[FinalGradeService],
) -> StudentGradeResponse:
    row = await service.set_result(
        current_user, course_id, student_id, FinalResult(body.grade, body.passed)
    )
    return StudentGradeResponse.model_validate(row, from_attributes=True)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_final_grade(
    course_id: UUID,
    student_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[FinalGradeService],
) -> None:
    await service.clear_result(current_user, course_id, student_id)
