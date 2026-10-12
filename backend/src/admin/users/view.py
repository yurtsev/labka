from typing import Any, ClassVar

from sqladmin import ModelView, action
from sqladmin.secret import Secret
from sqlalchemy import Select, func, select
from starlette.requests import Request
from starlette.responses import Response

from src.admin.di import resolve
from src.admin.users.service import AdminUserService
from src.admin.utils import selected_ids
from src.core.db.enums import UserRole
from src.core.db.models import User
from src.core.errors import DomainError


class UserView(ModelView, model=User):
    """Общее для разделов «Студенты» и «Преподаватели»: список только своей роли и действия
    деактивации, активации и сброса пароля.

    sqladmin выводит адрес раздела из имени модели (`/admin/user`) и затирает `identity`
    в классе с `model=`; у наследника свой адрес сохраняется.
    """

    role: ClassVar[UserRole]

    def list_query(self, request: Request) -> Select[Any]:
        return select(User).where(User.role == self.role)

    def count_query(self, request: Request) -> Select[Any]:
        return select(func.count(User.id)).where(User.role == self.role)

    def details_query(self, request: Request) -> Select[Any]:
        return super().details_query(request).where(User.role == self.role)

    def form_edit_query(self, request: Request) -> Select[Any]:
        return super().form_edit_query(request).where(User.role == self.role)

    @action(
        name="deactivate",
        label="Деактивировать",
        confirmation_message=(
            "Пользователи не смогут войти, их сессии завершатся; данные останутся. Продолжить?"
        ),
    )
    async def deactivate(self, request: Request) -> Response:
        return await self._set_active(request, False)

    @action(name="activate", label="Активировать")
    async def activate(self, request: Request) -> Response:
        return await self._set_active(request, True)

    @action(
        name="reset_password",
        label="Сбросить пароль",
        confirmation_message=(
            "Для каждого выбранного пользователя будет выдан новый пароль, "
            "все его сессии завершатся. Сбросить?"
        ),
    )
    async def reset_password(self, request: Request) -> Response:
        service = await resolve(request, AdminUserService)
        try:
            reset = await service.reset_passwords(self.role, selected_ids(request))
        except DomainError as exc:
            return await self._failed(request, exc)
        response = await self.templates.TemplateResponse(
            request,
            "admin/passwords.html",
            {
                "title": "Новые пароли",
                "passwords": reset,
                "back_url": str(request.url_for("admin:list", identity=self.identity)),
            },
        )
        Secret.apply_no_store_headers(response)
        return response

    async def _set_active(self, request: Request, active: bool) -> Response:
        service = await resolve(request, AdminUserService)
        try:
            changed = await service.set_active(self.role, selected_ids(request), active)
        except DomainError as exc:
            return await self._failed(request, exc)
        lines = [f"Пользователей {'активировано' if active else 'деактивировано'}: {changed}."]
        if not active:
            lines.append("Их сессии завершены.")
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
