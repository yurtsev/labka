from typing import Any
from uuid import UUID

from sqladmin import BaseView, ModelView, action, expose
from sqladmin.secret import Secret
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from wtforms.validators import Email, Optional

from src.admin.di import resolve
from src.admin.filters import LookupFilter
from src.admin.groups.dto import BatchFields, GroupFields
from src.admin.groups.parser import InviteListParser
from src.admin.groups.service import AdminGroupService
from src.admin.utils import normalize_email, selected_ids
from src.config import cfg
from src.core.db.enums import StudyForm, StudyLevel
from src.core.db.models import Course, CourseGroup, Direction, Faculty, Group, GroupInvite
from src.core.errors import DomainError


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
    column_filters = [
        LookupFilter.yes_no(
            "Активна",
            "active",
            lambda query, value: query.where(Group.is_active.is_(value == "true")),
        ),
        LookupFilter(
            "Подразделение",
            "faculty",
            lambda query, value: query.where(
                Group.direction_id.in_(
                    select(Direction.id).where(Direction.faculty_id == UUID(value))
                )
            ),
            options_query=select(Faculty.id, Faculty.short_name).order_by(Faculty.short_name),
        ),
        LookupFilter(
            "Направление",
            "direction",
            lambda query, value: query.where(Group.direction_id == UUID(value)),
            options_query=select(Direction.id, Direction.short_name).order_by(Direction.short_name),
        ),
        LookupFilter(
            "Уровень",
            "level",
            lambda query, value: query.where(Group.level == StudyLevel(value)),
            options=[(level.value, level.label) for level in StudyLevel],
        ),
        LookupFilter(
            "Форма обучения",
            "study_form",
            lambda query, value: query.where(Group.study_form == StudyForm(value)),
            options=[(form.value, form.label) for form in StudyForm],
        ),
        LookupFilter(
            "Курс",
            "course",
            lambda query, value: query.where(
                Group.id.in_(
                    select(CourseGroup.group_id).where(CourseGroup.course_id == UUID(value))
                )
            ),
            options_query=select(Course.id, Course.name).order_by(Course.name),
        ),
    ]
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

    @action(
        name="deactivate",
        label="Деактивировать группу",
        confirmation_message=(
            "Группу нельзя будет добавить в курс, по её коду нельзя будет зарегистрироваться. "
            "Студенты группы останутся активными. Продолжить?"
        ),
    )
    async def deactivate(self, request: Request) -> Response:
        return await self._set_active(request, False, with_students=False)

    @action(
        name="deactivate_with_students",
        label="Деактивировать группу и её студентов",
        confirmation_message=(
            "Студенты группы тоже не смогут войти, их сессии завершатся; данные останутся. "
            "Продолжить?"
        ),
    )
    async def deactivate_with_students(self, request: Request) -> Response:
        return await self._set_active(request, False, with_students=True)

    @action(name="activate", label="Активировать группу")
    async def activate(self, request: Request) -> Response:
        return await self._set_active(request, True, with_students=False)

    @action(name="show_students", label="Студенты группы", add_in_list=False)
    async def show_students(self, request: Request) -> Response:
        [group_id, *_] = selected_ids(request)
        return RedirectResponse(
            request.url_for("admin:list", identity="student").include_query_params(
                group=str(group_id)
            ),
            status_code=302,
        )

    @action(name="show_invites", label="Почты группы", add_in_list=False)
    async def show_invites(self, request: Request) -> Response:
        [group_id, *_] = selected_ids(request)
        return RedirectResponse(
            request.url_for("admin:list", identity="group-invite").include_query_params(
                group=str(group_id)
            ),
            status_code=302,
        )

    async def _set_active(self, request: Request, active: bool, *, with_students: bool) -> Response:
        service = await resolve(request, AdminGroupService)
        try:
            changed = await service.set_active(
                selected_ids(request), active, with_students=with_students
            )
        except DomainError as exc:
            return await self._failed(request, exc)
        lines = [f"Групп {'активировано' if active else 'деактивировано'}: {changed}."]
        if with_students:
            lines.append("Студенты этих групп деактивированы, их сессии завершены.")
        return await self.templates.TemplateResponse(
            request,
            "admin/result.html",
            {
                "title": "Готово",
                "lines": lines,
                "back_url": str(request.url_for("admin:list", identity=self.identity)),
            },
        )

    async def _failed(self, request: Request, error: DomainError) -> Response:
        return await self.templates.TemplateResponse(
            request,
            "admin/result.html",
            {
                "title": "Не получилось",
                "lines": [error.message],
                "back_url": str(request.url_for("admin:list", identity=self.identity)),
            },
        )

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
    column_filters = [
        LookupFilter(
            "Группа",
            "group",
            lambda query, value: query.where(GroupInvite.group_id == UUID(value)),
            options_query=select(Group.id, Group.name).order_by(Group.name),
        ),
        LookupFilter.yes_no(
            "Зарегистрирован",
            "registered",
            lambda query, value: query.where(
                GroupInvite.user_id.is_not(None)
                if value == "true"
                else GroupInvite.user_id.is_(None)
            ),
        ),
    ]
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


class BatchGroupsView(BaseView):
    name = "Создать группы пачкой"
    icon = "fa-solid fa-layer-group"
    category = "Группы и почты"

    @expose("/groups-batch", methods=["GET", "POST"], identity="groups-batch")
    async def batch(self, request: Request) -> Response:
        service = await resolve(request, AdminGroupService)
        form = {
            "direction": "",
            "level": StudyLevel.BACHELOR.value,
            "study_form": StudyForm.FULL_TIME.value,
            "admission_year": "",
            "count": "1",
        }
        context: dict[str, Any] = {}
        if request.method == "POST":
            form = {key: str(value) for key, value in (await request.form()).items()}
            try:
                created = await service.create_batch(
                    BatchFields(
                        direction_id=UUID(form["direction"]),
                        level=StudyLevel(form["level"]),
                        study_form=StudyForm(form["study_form"]),
                        admission_year=int(form["admission_year"]),
                        count=int(form["count"]),
                    )
                )
            except DomainError as exc:
                context = {"error": exc.message, "taken": exc.context.get("names")}
            except KeyError, ValueError:
                context = {"error": "Заполните все поля формы"}
            else:
                context = {
                    "created": created,
                    "groups_url": str(request.url_for("admin:list", identity="group")),
                }
        response = await self.templates.TemplateResponse(
            request,
            "admin/batch_groups.html",
            {
                "directions": await service.list_directions(),
                "levels": [(level.value, level.label) for level in StudyLevel],
                "study_forms": [(form_.value, form_.label) for form_ in StudyForm],
                "max_count": cfg.administration.max_batch_groups,
                "form": form,
                "groups_url": str(request.url_for("admin:list", identity="group")),
                **context,
            },
        )
        if "created" in context:
            Secret.apply_no_store_headers(response)
        return response


class InviteImportView(BaseView):
    name = "Загрузить почты"
    icon = "fa-solid fa-file-import"
    category = "Группы и почты"

    @expose("/invites-import", methods=["GET", "POST"], identity="invites-import")
    async def import_invites(self, request: Request) -> Response:
        service = await resolve(request, AdminGroupService)
        context: dict[str, Any] = {"form_group": "", "form_emails": ""}
        if request.method == "POST":
            form = await request.form()
            context["form_group"] = str(form.get("group", ""))
            context["form_emails"] = str(form.get("emails", ""))
            tokens = InviteListParser.from_text(context["form_emails"])
            upload = form.get("csv")
            if upload is not None and not isinstance(upload, str):
                tokens += InviteListParser.from_csv(await upload.read())
            try:
                context["report"] = await service.import_invites(
                    UUID(context["form_group"]), tokens
                )
            except DomainError as exc:
                context["error"] = exc.message
            except ValueError:
                context["error"] = "Выберите группу"
        return await self.templates.TemplateResponse(
            request,
            "admin/invites_import.html",
            {
                "groups": await service.list_groups(),
                "invites_url": str(request.url_for("admin:list", identity="group-invite")),
                "import_url": str(request.url_for("admin:view-invites-import")),
                **context,
            },
        )
