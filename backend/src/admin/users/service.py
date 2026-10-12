from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.admin.exc.users import (
    TargetGroupInactiveError,
    TargetGroupNotFoundError,
    UsersNotFoundError,
)
from src.admin.users.dto import ResetPassword, StudentRef
from src.core.db.enums import UserRole
from src.core.db.models.user import User
from src.core.db.uow import UnitOfWork
from src.core.security.service import SecurityService


class AdminUserService:
    """Студенты и преподаватели: деактивация, сброс пароля, перевод студентов."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    async def set_active(self, role: UserRole, user_ids: Sequence[UUID], active: bool) -> int:
        """Деактивирует или возвращает пользователей; деактивация завершает их сессии.

        Данные остаются, активировать можно обратно.

        Returns:
            Сколько пользователей изменено.

        Raises:
            UsersNotFoundError: никого из выбранных нет.
        """
        users = await self._find(role, user_ids)
        for user in users:
            user.is_active = active
        if not active:
            await self._uow.sessions.revoke_all_for_users(
                [user.id for user in users], datetime.now(UTC)
            )
        await self._uow.commit()
        return len(users)

    async def reset_passwords(
        self, role: UserRole, user_ids: Sequence[UUID]
    ) -> list[ResetPassword]:
        """Выдаёт пользователям новые пароли и завершает все их сессии.

        Returns:
            Пароли в открытом виде: в БД остаётся хэш, показать пароль можно только сейчас.

        Raises:
            UsersNotFoundError: никого из выбранных нет.
        """
        users = await self._find(role, user_ids)
        reset = []
        for user in users:
            password = self._security.generate_password()
            user.password_hash = self._security.hash_password(password)
            reset.append(
                ResetPassword(
                    user_id=user.id,
                    full_name=self._full_name(user),
                    email=user.email,
                    password=password,
                )
            )
        await self._uow.sessions.revoke_all_for_users(
            [user.id for user in users], datetime.now(UTC)
        )
        await self._uow.commit()
        return reset

    async def transfer_students(self, student_ids: Sequence[UUID], group_id: UUID) -> int:
        """Переводит студентов в другую активную группу.

        Студенты сразу видят курсы новой группы, курсы старой пропадают, их попытки остаются.

        Returns:
            Сколько студентов переведено.

        Raises:
            TargetGroupNotFoundError: группы нет.
            TargetGroupInactiveError: группа неактивна.
            UsersNotFoundError: никого из выбранных нет.
        """
        group = await self._uow.groups.get_by_id(group_id)
        if group is None:
            raise TargetGroupNotFoundError({"group_id": str(group_id)})
        if not group.is_active:
            raise TargetGroupInactiveError({"group_id": str(group_id)})
        students = await self._find(UserRole.STUDENT, student_ids)
        for student in students:
            student.group_id = group.id
        await self._uow.commit()
        return len(students)

    async def students(self, student_ids: Sequence[UUID]) -> list[StudentRef]:
        """Выбранные студенты с группами — для страницы подтверждения перевода."""
        found = await self._find(UserRole.STUDENT, student_ids)
        groups = {
            group.id: group.name
            for group in await self._uow.groups.get_many({s.group_id for s in found if s.group_id})
        }
        return [
            StudentRef(
                id=student.id,
                full_name=self._full_name(student),
                group_name=groups.get(student.group_id, "") if student.group_id else "",
            )
            for student in found
        ]

    async def _find(self, role: UserRole, user_ids: Sequence[UUID]) -> list[User]:
        users = await self._uow.users.list_by_role(role, user_ids)
        if not users:
            raise UsersNotFoundError({"user_ids": [str(item) for item in user_ids]})
        return users

    @staticmethod
    def _full_name(user: User) -> str:
        return " ".join(
            part for part in (user.last_name, user.first_name, user.middle_name) if part
        )
