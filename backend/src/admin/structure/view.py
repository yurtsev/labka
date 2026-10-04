from typing import Any
from uuid import UUID

from sqladmin import ModelView
from starlette.requests import Request

from src.admin.di import resolve
from src.admin.structure.dto import DepartmentFields, DirectionFields, FacultyFields
from src.admin.structure.service import AdminStructureService
from src.core.db.enums import FacultyType
from src.core.db.models import Department, Direction, Faculty


class FacultyView(ModelView, model=Faculty):
    name = "Подразделение"
    name_plural = "Подразделения"
    icon = "fa-solid fa-building-columns"
    category = "Структура вуза"
    column_list = [Faculty.short_name, Faculty.name, Faculty.type]
    column_searchable_list = [Faculty.name, Faculty.short_name]
    column_sortable_list = [Faculty.short_name, Faculty.name]
    form_columns = [Faculty.name, Faculty.short_name, Faculty.type]
    column_labels = {
        Faculty.name: "Название",
        Faculty.short_name: "Сокращение",
        Faculty.type: "Тип",
    }

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        # sqladmin нужен только идентификатор созданной записи — для ссылок после сохранения.
        return Faculty(id=await service.create_faculty(self._fields(data)))

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        await service.update_faculty(UUID(pk), self._fields(data))
        return Faculty(id=UUID(pk))

    async def delete_model(self, request: Request, pk: str) -> None:
        service = await resolve(request, AdminStructureService)
        await service.delete_faculty(UUID(pk))

    @staticmethod
    def _fields(data: dict[str, Any]) -> FacultyFields:
        return FacultyFields(
            name=data["name"].strip(),
            short_name=data["short_name"].strip(),
            type=FacultyType(data["type"]),
        )


class DepartmentView(ModelView, model=Department):
    name = "Кафедра"
    name_plural = "Кафедры"
    icon = "fa-solid fa-chalkboard-user"
    category = "Структура вуза"
    column_list = [Department.name, Department.faculty]
    column_searchable_list = [Department.name]
    column_sortable_list = [Department.name]
    form_columns = [Department.faculty, Department.name]
    column_labels = {Department.name: "Название", Department.faculty: "Подразделение"}

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        return Department(id=await service.create_department(self._fields(data)))

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        await service.update_department(UUID(pk), self._fields(data))
        return Department(id=UUID(pk))

    async def delete_model(self, request: Request, pk: str) -> None:
        service = await resolve(request, AdminStructureService)
        await service.delete_department(UUID(pk))

    @staticmethod
    def _fields(data: dict[str, Any]) -> DepartmentFields:
        return DepartmentFields(faculty_id=UUID(data["faculty"]), name=data["name"].strip())


class DirectionView(ModelView, model=Direction):
    name = "Направление"
    name_plural = "Направления"
    icon = "fa-solid fa-signs-post"
    category = "Структура вуза"
    column_list = [Direction.short_name, Direction.name, Direction.faculty]
    column_searchable_list = [Direction.short_name, Direction.name]
    column_sortable_list = [Direction.short_name, Direction.name]
    form_columns = [Direction.faculty, Direction.short_name, Direction.name]
    column_labels = {
        Direction.short_name: "Сокращение",
        Direction.name: "Название",
        Direction.faculty: "Подразделение",
    }

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        return Direction(id=await service.create_direction(self._fields(data)))

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminStructureService)
        await service.update_direction(UUID(pk), self._fields(data))
        return Direction(id=UUID(pk))

    async def delete_model(self, request: Request, pk: str) -> None:
        service = await resolve(request, AdminStructureService)
        await service.delete_direction(UUID(pk))

    @staticmethod
    def _fields(data: dict[str, Any]) -> DirectionFields:
        return DirectionFields(
            faculty_id=UUID(data["faculty"]),
            short_name=data["short_name"].strip(),
            name=data["name"].strip(),
        )
