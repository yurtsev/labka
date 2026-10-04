import logging
from pathlib import Path

import sqladmin.application
from fastapi import FastAPI
from sqladmin import Admin
from sqladmin.i18n import I18nConfig

from src.admin.auth.backend import AdminAuthBackend
from src.admin.error_reporter import AdminErrorReporter
from src.admin.groups.view import GroupInviteView, GroupView
from src.admin.structure.view import DepartmentView, DirectionView, FacultyView
from src.admin.teachers.view import TeacherView
from src.core.db.db import Session


class AdminSite:
    """Сборка sqladmin на `/admin`: вход, шаблоны и разделы админки."""

    @staticmethod
    def mount(app: FastAPI) -> None:
        admin = Admin(
            app,
            session_maker=Session,
            base_url="/admin",
            title="Labka",
            authentication_backend=AdminAuthBackend(),
            templates_dir=str(Path(__file__).parent / "templates"),
            # Только русский: язык браузера и cookie выбора языка не учитываются.
            i18n_config=I18nConfig(
                default_locale="ru", language_cookie_name=None, language_header_name=None
            ),
        )
        logging.getLogger(sqladmin.application.__name__).addFilter(AdminErrorReporter())
        for view in (
            FacultyView,
            DepartmentView,
            DirectionView,
            GroupView,
            GroupInviteView,
            TeacherView,
        ):
            admin.add_view(view)
