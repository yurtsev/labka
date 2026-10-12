from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.pagination import PageNumber, PageResponse, PerPage
from src.api.reviews.dto import QueueFilter
from src.api.reviews.schemas import (
    AttemptResponse,
    QueueItemResponse,
    ReviewCorrectRequest,
    ReviewCreateRequest,
    StudentAttemptsResponse,
)
from src.api.reviews.service import ReviewService
from src.api.reviews.utils import review_correction, review_decision
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.security.dto import CurrentUser

router = APIRouter(tags=["reviews"], route_class=DishkaRoute)


@router.get("/reviews/queue")
async def review_queue(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ReviewService],
    course_id: UUID | None = None,
    assignment_id: UUID | None = None,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[QueueItemResponse]:
    queue = await service.queue(
        current_user,
        QueueFilter(course_id=course_id, assignment_id=assignment_id),
        PageRequest(page, per_page),
    )
    return PageResponse[QueueItemResponse].model_validate(queue, from_attributes=True)


@router.get("/courses/{course_id}/assignments/{assignment_id}/students/{student_id}/submissions")
async def student_submissions(
    course_id: UUID,
    assignment_id: UUID,
    student_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ReviewService],
) -> StudentAttemptsResponse:
    attempts = await service.student_attempts(current_user, course_id, assignment_id, student_id)
    return StudentAttemptsResponse.model_validate(attempts, from_attributes=True)


@router.post(
    "/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review",
    status_code=status.HTTP_201_CREATED,
)
async def review_submission(
    course_id: UUID,
    assignment_id: UUID,
    submission_id: UUID,
    body: ReviewCreateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ReviewService],
) -> AttemptResponse:
    attempt = await service.review(
        current_user, course_id, assignment_id, submission_id, review_decision(body)
    )
    return AttemptResponse.model_validate(attempt, from_attributes=True)


@router.put("/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review")
async def correct_review(
    course_id: UUID,
    assignment_id: UUID,
    submission_id: UUID,
    body: ReviewCorrectRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[ReviewService],
) -> AttemptResponse:
    attempt = await service.correct(
        current_user, course_id, assignment_id, submission_id, review_correction(body)
    )
    return AttemptResponse.model_validate(attempt, from_attributes=True)
