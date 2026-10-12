from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from src.api.assignments.dto import StudentRowsFilter
from src.api.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentResponse,
    AssignmentUpdateRequest,
    StudentRowResponse,
    UploadedFileRequest,
    UploadFormResponse,
    UploadStartRequest,
)
from src.api.assignments.service import AssignmentService
from src.api.assignments.utils import assignment_fields, uploaded_file
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.grading.enums import ProgressStatus
from src.core.security.dto import CurrentUser

router = APIRouter(
    prefix="/courses/{course_id}/assignments", tags=["assignments"], route_class=DishkaRoute
)


@router.post("/uploads")
async def start_assignment_upload(
    course_id: UUID,
    body: UploadStartRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> UploadFormResponse:
    form = await service.start_upload(current_user, course_id, body.content_type, body.file_size)
    return UploadFormResponse.model_validate(form, from_attributes=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    course_id: UUID,
    body: AssignmentCreateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> AssignmentResponse:
    assignment = await service.create(
        current_user,
        course_id,
        assignment_fields(body),
        [uploaded_file(file) for file in body.files],
    )
    return AssignmentResponse.model_validate(assignment, from_attributes=True)


@router.get("/{assignment_id}")
async def get_assignment(
    course_id: UUID,
    assignment_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> AssignmentResponse:
    assignment = await service.get(current_user, course_id, assignment_id)
    return AssignmentResponse.model_validate(assignment, from_attributes=True)


@router.put("/{assignment_id}")
async def update_assignment(
    course_id: UUID,
    assignment_id: UUID,
    body: AssignmentUpdateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> AssignmentResponse:
    assignment = await service.update(
        current_user, course_id, assignment_id, assignment_fields(body)
    )
    return AssignmentResponse.model_validate(assignment, from_attributes=True)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    course_id: UUID,
    assignment_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> None:
    await service.delete(current_user, course_id, assignment_id)


@router.post("/{assignment_id}/files", status_code=status.HTTP_201_CREATED)
async def add_assignment_file(
    course_id: UUID,
    assignment_id: UUID,
    body: UploadedFileRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> AssignmentResponse:
    assignment = await service.add_file(current_user, course_id, assignment_id, uploaded_file(body))
    return AssignmentResponse.model_validate(assignment, from_attributes=True)


@router.delete("/{assignment_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment_file(
    course_id: UUID,
    assignment_id: UUID,
    file_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
) -> None:
    await service.delete_file(current_user, course_id, assignment_id, file_id)


@router.get("/{assignment_id}/students")
async def list_assignment_students(
    course_id: UUID,
    assignment_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[AssignmentService],
    group_id: UUID | None = None,
    progress_status: Annotated[ProgressStatus | None, Query(alias="status")] = None,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[StudentRowResponse]:
    rows = await service.student_rows(
        current_user,
        course_id,
        assignment_id,
        StudentRowsFilter(group_id=group_id, status=progress_status),
        PageRequest(page, per_page),
    )
    return PageResponse[StudentRowResponse].model_validate(rows, from_attributes=True)
