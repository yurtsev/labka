from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.courses.schemas import (
    AdmissionYearQuery,
    CourseCreateRequest,
    CourseGroupAddRequest,
    CoursePreviewResponse,
    CourseResponse,
    CourseUpdateRequest,
    GroupNameQuery,
    GroupResponse,
)
from src.api.courses.service import CourseService
from src.api.courses.utils import course_fields
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.group import GroupSearch
from src.core.db.dto.page import PageRequest
from src.core.db.enums import StudyForm, StudyLevel
from src.core.security.dto import CurrentUser

router = APIRouter(prefix="/courses", tags=["courses"], route_class=DishkaRoute)


@router.get("")
async def list_courses(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
    archived: bool = False,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[CoursePreviewResponse]:
    courses = await service.list_courses(current_user, archived, PageRequest(page, per_page))
    return PageResponse[CoursePreviewResponse].model_validate(courses, from_attributes=True)


@router.get("/available-groups")
async def list_available_groups(
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
    query: GroupNameQuery = None,
    level: StudyLevel | None = None,
    study_form: StudyForm | None = None,
    admission_year: AdmissionYearQuery = None,
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[GroupResponse]:
    search = GroupSearch(
        query=(query or "").strip() or None,
        level=level,
        study_form=study_form,
        admission_year=admission_year,
    )
    groups = await service.list_available_groups(current_user, search, PageRequest(page, per_page))
    return PageResponse[GroupResponse].model_validate(groups, from_attributes=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.create_course(current_user, course_fields(body), body.group_ids)
    return CourseResponse.model_validate(course, from_attributes=True)


@router.get("/{course_id}")
async def get_course(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.get_course(current_user, course_id)
    return CourseResponse.model_validate(course, from_attributes=True)


@router.put("/{course_id}")
async def update_course(
    course_id: UUID,
    body: CourseUpdateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.update_course(current_user, course_id, course_fields(body))
    return CourseResponse.model_validate(course, from_attributes=True)


@router.post("/{course_id}/groups")
async def add_course_group(
    course_id: UUID,
    body: CourseGroupAddRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.add_group(current_user, course_id, body.group_id)
    return CourseResponse.model_validate(course, from_attributes=True)


@router.delete("/{course_id}/groups/{group_id}")
async def remove_course_group(
    course_id: UUID,
    group_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.remove_group(current_user, course_id, group_id)
    return CourseResponse.model_validate(course, from_attributes=True)


@router.post("/{course_id}/archive")
async def archive_course(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.set_archived(current_user, course_id, archived=True)
    return CourseResponse.model_validate(course, from_attributes=True)


@router.post("/{course_id}/unarchive")
async def unarchive_course(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[CourseService],
) -> CourseResponse:
    course = await service.set_archived(current_user, course_id, archived=False)
    return CourseResponse.model_validate(course, from_attributes=True)
