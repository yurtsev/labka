from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from src.admin.auth.enums import AdminCookie
from src.admin.auth.service import AdminAuthService
from src.admin.di import resolve
from src.config import cfg


class AdminAuthBackend(AuthenticationBackend):
    """HTTP-обвязка входа в sqladmin: форма входа ↔ cookie, решения принимает сервис."""

    def __init__(self) -> None:
        # Конструктор базового класса подключает подписанную cookie-сессию Starlette.
        # Она не нужна: в cookie лежит токен сессии, который проверяется по БД.
        self.middlewares = []

    async def login(self, request: Request) -> Response | bool:
        form = await request.form()
        service = await resolve(request, AdminAuthService)
        token = await service.login(
            str(form.get("username", "")).strip().lower(),
            str(form.get("password", "")),
            request.headers.get("user-agent"),
        )
        if token is None:
            return False
        response = RedirectResponse(request.url_for("admin:index"), status_code=302)
        response.set_cookie(
            AdminCookie.SESSION,
            token,
            max_age=cfg.auth.admin_session_ttl_hours * 60 * 60,
            path=request.url_for("admin:index").path,
            secure=cfg.auth.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return response

    async def logout(self, request: Request) -> Response | bool:
        service = await resolve(request, AdminAuthService)
        await service.logout(request.cookies.get(AdminCookie.SESSION))
        response = RedirectResponse(request.url_for("admin:login"), status_code=302)
        response.delete_cookie(
            AdminCookie.SESSION,
            path=request.url_for("admin:index").path,
            secure=cfg.auth.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return response

    async def authenticate(self, request: Request) -> Response | bool:
        service = await resolve(request, AdminAuthService)
        return await service.authenticate(request.cookies.get(AdminCookie.SESSION)) is not None
