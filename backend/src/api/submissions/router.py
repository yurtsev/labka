from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.submissions.schemas import (
    AttemptResponse,
    AttemptsResponse,
    SubmissionCreateRequest,
    UploadFormResponse,
    UploadStartRequest,
)
from src.api.submissions.service import SubmissionService
from src.api.submissions.utils import uploaded_file
from src.core.security.dto import CurrentUser

router = APIRouter(
    prefix="/courses/{course_id}/assignments/{assignment_id}/submissions",
    tags=["submissions"],
    route_class=DishkaRoute,
)


@router.post("/uploads")
async def start_submission_upload(
    course_id: UUID,
    assignment_id: UUID,
    body: UploadStartRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[SubmissionService],
) -> UploadFormResponse:
    form = await service.start_upload(
        current_user, course_id, assignment_id, body.content_type, body.file_size
    )
    return UploadFormResponse.model_validate(form, from_attributes=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit(
    course_id: UUID,
    assignment_id: UUID,
    body: SubmissionCreateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[SubmissionService],
) -> AttemptResponse:
    attempt = await service.submit(
        current_user,
        course_id,
        assignment_id,
        body.comment or None,
        [uploaded_file(file) for file in body.files],
    )
    return AttemptResponse.model_validate(attempt, from_attributes=True)


@router.get("")
async def list_my_submissions(
    course_id: UUID,
    assignment_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[SubmissionService],
) -> AttemptsResponse:
    attempts = await service.history(current_user, course_id, assignment_id)
    return AttemptsResponse.model_validate(attempts, from_attributes=True)
