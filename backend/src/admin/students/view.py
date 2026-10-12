from typing import Any
from uuid import UUID

from sqladmin import BaseView, action, expose
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from src.admin.di import resolve
from src.admin.filters import LookupFilter
from src.admin.groups.service import AdminGroupService
from src.admin.users.service import AdminUserService
from src.admin.users.view import UserView
from src.admin.utils import selected_ids
from src.core.db.enums import UserRole
from src.core.db.models import Group, User
from src.core.errors import DomainError


class StudentView(UserView):
    identity = "student"
    name = "Студент"
    name_plural = "Студенты"
    icon = "fa-solid fa-user-graduate"
    category = "Пользователи"
    role = UserRole.STUDENT
    # Студенты регистрируются сами по коду группы; админ только переводит и деактивирует.
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        User.last_name,
        User.first_name,
        User.middle_name,
        User.email,
        User.group,
        User.is_active,
    ]
    column_details_list = [*column_list, User.created_at]
    column_searchable_list = [User.last_name, User.first_name, User.email]
    column_sortable_list = [User.last_name, User.email]
    column_default_sort = [(User.last_name, False)]
    column_filters = [
        LookupFilter(
            "Группа",
            "group",
            lambda query, value: query.where(User.group_id == UUID(value)),
            options_query=select(Group.id, Group.name).order_by(Group.name),
        ),
        LookupFilter.yes_no(
            "Активен",
            "active",
            lambda query, value: query.where(User.is_active.is_(value == "true")),
        ),
    ]
    column_labels = {
        User.last_name: "Фамилия",
        User.first_name: "Имя",
        User.middle_name: "Отчество",
        User.email: "Почта",
        User.group: "Группа",
        User.is_active: "Активен",
        User.created_at: "Зарегистрирован",
    }

    @action(name="transfer", label="Перевести в другую группу")
    async def transfer(self, request: Request) -> Response:
        pks = ",".join(str(item) for item in selected_ids(request))
        return RedirectResponse(
            request.url_for("admin:view-students-transfer").include_query_params(pks=pks),
            status_code=302,
        )


class TransferStudentsView(BaseView):
    name = "Перевод студентов"
    icon = "fa-solid fa-right-left"

    def is_visible(self, request: Request) -> bool:
        """Страница открывается только из действия в списке студентов."""
        return False

    @expose("/students-transfer", methods=["GET", "POST"], identity="students-transfer")
    async def transfer(self, request: Request) -> Response:
        service = await resolve(request, AdminUserService)
        group_service = await resolve(request, AdminGroupService)
        student_ids = selected_ids(request)
        back_url = str(request.url_for("admin:list", identity="student"))
        context: dict[str, Any] = {"error": None}
        if request.method == "POST":
            form = await request.form()
            try:
                moved = await service.transfer_students(student_ids, UUID(str(form.get("group"))))
            except DomainError as exc:
                context["error"] = exc.message
            except ValueError:
                context["error"] = "Выберите группу"
            else:
                return await self.templates.TemplateResponse(
                    request,
                    "admin/result.html",
                    {
                        "title": "Готово",
                        "lines": [f"Студентов переведено: {moved}."],
                        "back_url": back_url,
                    },
                )
        try:
            students = await service.students(student_ids)
        except DomainError as exc:
            context["error"] = exc.message
            students = []
        return await self.templates.TemplateResponse(
            request,
            "admin/transfer.html",
            {
                "students": students,
                "groups": await group_service.list_active_groups(),
                "pks": ",".join(str(item) for item in student_ids),
                "back_url": back_url,
                **context,
            },
        )
