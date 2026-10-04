from typing import Any
from uuid import UUID

from sqladmin import ModelView
from sqladmin.secret import Secret
from sqlalchemy import Select, func, select
from starlette.requests import Request
from wtforms.validators import DataRequired, Email

from src.admin.di import resolve
from src.admin.teachers.dto import TeacherFields
from src.admin.teachers.service import AdminTeacherService
from src.admin.utils import normalize_email
from src.core.db.enums import UserRole
from src.core.db.models import User


class _UserModelView(ModelView, model=User):
    """Привязка к `User`. sqladmin выводит адрес раздела из имени модели (`/admin/user`)
    и затирает `identity` в классе с `model=`; у наследника свой адрес сохраняется."""


class TeacherView(_UserModelView):
    identity = "teacher"
    name = "Преподаватель"
    name_plural = "Преподаватели"
    icon = "fa-solid fa-user-tie"
    category = "Пользователи"
    can_delete = False
    column_list = [
        User.last_name,
        User.first_name,
        User.middle_name,
        User.email,
        User.department,
        User.is_active,
    ]
    column_details_list = [*column_list, User.teaching_groups, User.created_at]
    column_searchable_list = [User.last_name, User.email]
    column_sortable_list = [User.last_name, User.email]
    column_default_sort = [(User.last_name, False)]
    form_columns = [
        User.last_name,
        User.first_name,
        User.middle_name,
        User.email,
        User.department,
        User.teaching_groups,
    ]
    form_args = {
        "email": {
            "validators": [Email()],
            "filters": [normalize_email],
        },
        "department": {"allow_blank": False, "validators": [DataRequired()]},
    }
    column_labels = {
        User.last_name: "Фамилия",
        User.first_name: "Имя",
        User.middle_name: "Отчество",
        User.email: "Почта",
        User.department: "Кафедра",
        User.teaching_groups: "Прикреплённые группы",
        User.is_active: "Активен",
        User.created_at: "Создан",
    }

    def list_query(self, request: Request) -> Select[Any]:
        return select(User).where(User.role == UserRole.TEACHER)

    def count_query(self, request: Request) -> Select[Any]:
        return select(func.count(User.id)).where(User.role == UserRole.TEACHER)

    def details_query(self, request: Request) -> Select[Any]:
        return super().details_query(request).where(User.role == UserRole.TEACHER)

    def form_edit_query(self, request: Request) -> Select[Any]:
        return super().form_edit_query(request).where(User.role == UserRole.TEACHER)

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminTeacherService)
        created = await service.create(self._fields(data))
        Secret.reveal_once(
            request,
            created.password,
            title="Пароль преподавателя",
            label="Передайте пароль преподавателю. Больше его показать нельзя.",
        )
        # sqladmin нужен только идентификатор созданной записи — для ссылок после сохранения.
        return User(id=created.teacher_id)

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminTeacherService)
        await service.update(UUID(pk), self._fields(data))
        return User(id=UUID(pk))

    @staticmethod
    def _fields(data: dict[str, Any]) -> TeacherFields:
        return TeacherFields(
            last_name=data["last_name"].strip(),
            first_name=data["first_name"].strip(),
            middle_name=(data.get("middle_name") or "").strip() or None,
            email=data["email"],
            department_id=UUID(data["department"]),
            group_ids=frozenset(UUID(pk) for pk in data.get("teaching_groups") or ()),
        )
