from typing import Any
from uuid import UUID

from sqladmin import ModelView, action
from sqladmin.secret import Secret
from starlette.requests import Request
from starlette.responses import Response
from wtforms.validators import Email, Optional

from src.admin.di import resolve
from src.admin.groups.dto import GroupFields
from src.admin.groups.service import AdminGroupService
from src.admin.utils import normalize_email
from src.core.db.enums import StudyForm, StudyLevel
from src.core.db.models import Group, GroupInvite


class GroupView(ModelView, model=Group):
    name = "Группа"
    name_plural = "Группы"
    icon = "fa-solid fa-people-group"
    category = "Группы и почты"
    can_delete = False
    column_list = [
        Group.name,
        Group.direction,
        Group.level,
        Group.study_form,
        Group.admission_year,
        Group.is_active,
    ]
    column_details_list = column_list
    column_searchable_list = [Group.name]
    column_sortable_list = [Group.name, Group.admission_year]
    column_default_sort = [(Group.name, False)]
    form_columns = [
        Group.direction,
        Group.level,
        Group.study_form,
        Group.admission_year,
        Group.number,
        Group.name,
    ]
    form_args = {
        "name": {
            "validators": [Optional()],
            "description": "Оставьте пустым — соберётся автоматически, например БВТ2601",
        },
    }
    column_labels = {
        Group.name: "Название",
        Group.direction: "Направление",
        Group.level: "Уровень",
        Group.study_form: "Форма обучения",
        Group.admission_year: "Год набора",
        Group.number: "Номер",
        Group.is_active: "Активна",
    }

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminGroupService)
        created = await service.create(self._fields(data))
        self._reveal_code(request, created.registration_code)
        # sqladmin нужен только идентификатор созданной записи — для ссылок после сохранения.
        return Group(id=created.group_id)

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminGroupService)
        await service.update(UUID(pk), self._fields(data))
        return Group(id=UUID(pk))

    @action(
        name="reissue_code",
        label="Перевыпустить код",
        confirmation_message="Старый код перестанет действовать. Перевыпустить?",
        add_in_list=False,
    )
    async def reissue_code(self, request: Request) -> Response:
        group_id = UUID(request.query_params["pks"])
        service = await resolve(request, AdminGroupService)
        self._reveal_code(request, await service.reissue_code(group_id))
        next_url = request.url_for("admin:details", identity=self.identity, pk=str(group_id))
        response = await self.templates.TemplateResponse(
            request,
            "admin/secret.html",
            {"title": self.name, "secret_next_url": str(next_url)},
        )
        Secret.apply_no_store_headers(response)
        return response

    @staticmethod
    def _fields(data: dict[str, Any]) -> GroupFields:
        return GroupFields(
            direction_id=UUID(data["direction"]),
            level=StudyLevel(data["level"]),
            study_form=StudyForm(data["study_form"]),
            admission_year=int(data["admission_year"]),
            number=int(data["number"]),
            name=(data.get("name") or "").strip() or None,
        )

    @staticmethod
    def _reveal_code(request: Request, code: str) -> None:
        Secret.reveal_once(
            request,
            code,
            title="Код регистрации группы",
            label="Передайте код группе. Больше его показать нельзя — только перевыпустить.",
        )


class GroupInviteView(ModelView, model=GroupInvite):
    name = "Почта группы"
    name_plural = "Почты групп"
    icon = "fa-solid fa-envelope"
    category = "Группы и почты"
    column_list = [
        GroupInvite.email,
        GroupInvite.group,
        GroupInvite.user_id,
        GroupInvite.created_at,
    ]
    column_details_list = column_list
    column_searchable_list = [GroupInvite.email]
    column_sortable_list = [GroupInvite.email, GroupInvite.created_at]
    column_default_sort = [(GroupInvite.created_at, True)]
    column_formatters = {
        GroupInvite.user_id: lambda invite, _: "да" if invite.user_id else "нет",
    }
    column_formatters_detail = column_formatters
    form_columns = [GroupInvite.group, GroupInvite.email]
    form_create_rules = ["group", "email"]
    form_edit_rules = ["group"]
    form_args = {
        "email": {
            "validators": [Email()],
            "filters": [normalize_email],
        },
    }
    column_labels = {
        GroupInvite.email: "Почта",
        GroupInvite.group: "Группа",
        GroupInvite.user_id: "Зарегистрирован",
        GroupInvite.created_at: "Добавлена",
    }

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminGroupService)
        invite_id = await service.add_invite(UUID(data["group"]), data["email"])
        return GroupInvite(id=invite_id)

    async def update_model(self, request: Request, pk: str, data: dict[str, Any]) -> Any:
        service = await resolve(request, AdminGroupService)
        await service.move_invite(UUID(pk), UUID(data["group"]))
        return GroupInvite(id=UUID(pk))
