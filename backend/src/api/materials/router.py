from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.api.materials.schemas import (
    MaterialCreateRequest,
    MaterialResponse,
    MaterialUpdateRequest,
    UploadedFileRequest,
    UploadFormResponse,
    UploadStartRequest,
)
from src.api.materials.service import MaterialService
from src.api.materials.utils import material_fields, uploaded_file
from src.api.pagination import PageNumber, PageResponse, PerPage
from src.config import cfg
from src.core.db.dto.page import PageRequest
from src.core.security.dto import CurrentUser

router = APIRouter(
    prefix="/courses/{course_id}/materials", tags=["materials"], route_class=DishkaRoute
)


@router.get("")
async def list_materials(
    course_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
    page: PageNumber = 1,
    per_page: PerPage = cfg.pagination.default_per_page,
) -> PageResponse[MaterialResponse]:
    materials = await service.list_materials(current_user, course_id, PageRequest(page, per_page))
    return PageResponse[MaterialResponse].model_validate(materials, from_attributes=True)


@router.post("/uploads")
async def start_material_upload(
    course_id: UUID,
    body: UploadStartRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> UploadFormResponse:
    form = await service.start_upload(current_user, course_id, body.content_type, body.file_size)
    return UploadFormResponse.model_validate(form, from_attributes=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_material(
    course_id: UUID,
    body: MaterialCreateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> MaterialResponse:
    material = await service.create_material(
        current_user,
        course_id,
        material_fields(body),
        [uploaded_file(file) for file in body.files],
    )
    return MaterialResponse.model_validate(material, from_attributes=True)


@router.put("/{material_id}")
async def update_material(
    course_id: UUID,
    material_id: UUID,
    body: MaterialUpdateRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> MaterialResponse:
    material = await service.update_material(
        current_user, course_id, material_id, material_fields(body)
    )
    return MaterialResponse.model_validate(material, from_attributes=True)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    course_id: UUID,
    material_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> None:
    await service.delete_material(current_user, course_id, material_id)


@router.post("/{material_id}/files", status_code=status.HTTP_201_CREATED)
async def add_material_file(
    course_id: UUID,
    material_id: UUID,
    body: UploadedFileRequest,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> MaterialResponse:
    material = await service.add_file(current_user, course_id, material_id, uploaded_file(body))
    return MaterialResponse.model_validate(material, from_attributes=True)


@router.delete("/{material_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_file(
    course_id: UUID,
    material_id: UUID,
    file_id: UUID,
    current_user: FromDishka[CurrentUser],
    service: FromDishka[MaterialService],
) -> None:
    await service.delete_file(current_user, course_id, material_id, file_id)
