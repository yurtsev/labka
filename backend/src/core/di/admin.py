from dishka import Provider, Scope, provide

from src.admin.accounts.service import AdminAccountService
from src.admin.auth.service import AdminAuthService
from src.admin.groups.service import AdminGroupService
from src.admin.structure.service import AdminStructureService
from src.admin.teachers.service import AdminTeacherService
from src.admin.users.service import AdminUserService


class AdminProvider(Provider):
    admin_auth_service = provide(AdminAuthService, scope=Scope.REQUEST)
    admin_account_service = provide(AdminAccountService, scope=Scope.REQUEST)
    admin_group_service = provide(AdminGroupService, scope=Scope.REQUEST)
    admin_structure_service = provide(AdminStructureService, scope=Scope.REQUEST)
    admin_teacher_service = provide(AdminTeacherService, scope=Scope.REQUEST)
    admin_user_service = provide(AdminUserService, scope=Scope.REQUEST)
