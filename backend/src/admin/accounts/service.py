from uuid import UUID, uuid7

from src.admin.accounts.dto import NewAdmin
from src.admin.exc.accounts import AdminEmailTakenError
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.user import User
from src.core.db.uow import UnitOfWork
from src.core.security.service import SecurityService


class AdminAccountService:
    """Учётные записи админов. Админа нельзя создать из веб-приложения или админки —
    только командой `make create-admin` на сервере."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    async def create_admin(self, new_admin: NewAdmin) -> UUID:
        """Создаёт активного админа с заданным паролем.

        Raises:
            AdminEmailTakenError: пользователь с этой почтой уже есть.
        """
        admin = User(
            id=uuid7(),
            last_name=new_admin.last_name,
            first_name=new_admin.first_name,
            middle_name=new_admin.middle_name,
            email=new_admin.email,
            password_hash=self._security.hash_password(new_admin.password),
            role=UserRole.ADMIN,
        )
        self._uow.users.add(admin)
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_users_email":
                raise AdminEmailTakenError from exc
            raise
        return admin.id
