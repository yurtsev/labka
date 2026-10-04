from uuid import UUID, uuid7

from src.admin.exc.groups import (
    DirectionNotFoundError,
    GroupNameTakenError,
    GroupNotFoundError,
    InviteEmailTakenError,
    InviteNotFoundError,
)
from src.admin.groups.dto import CreatedGroup, GroupFields
from src.core.db.enums import StudyLevel
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.direction import Direction
from src.core.db.models.group import Group
from src.core.db.models.group_invite import GroupInvite
from src.core.db.uow import UnitOfWork
from src.core.security.service import SecurityService


class AdminGroupService:
    """Группы и списки их почт: всё, что админ делает с группой."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    async def create(self, fields: GroupFields) -> CreatedGroup:
        """Создаёт группу и выпускает ей код регистрации.

        Returns:
            Id группы и код в открытом виде: в БД лежит только хэш, показать код можно один раз.

        Raises:
            DirectionNotFoundError: направления нет.
            GroupNameTakenError: группа с таким названием уже есть.
        """
        code = self._security.issue_registration_code()
        group = Group(id=uuid7(), registration_code_hash=self._security.hash_token(code))
        await self._apply_fields(group, fields, fields.name)
        self._uow.groups.add(group)
        await self._commit_group()
        return CreatedGroup(group_id=group.id, registration_code=code)

    async def update(self, group_id: UUID, fields: GroupFields) -> None:
        """Меняет поля группы.

        Пустое название собирается заново. Автоматическое название, которое не правили
        вручную, пересобирается по новым полям; ручное остаётся как есть.

        Raises:
            GroupNotFoundError: группы нет.
            DirectionNotFoundError: направления нет.
            GroupNameTakenError: группа с таким названием уже есть.
        """
        group = await self._get_group(group_id)
        old_direction = await self._get_direction(group.direction_id)
        old_auto_name = self._auto_name(
            old_direction, group.level, group.admission_year, group.number
        )
        is_auto_name_kept = fields.name == group.name == old_auto_name
        await self._apply_fields(group, fields, None if is_auto_name_kept else fields.name)
        await self._commit_group()

    async def reissue_code(self, group_id: UUID) -> str:
        """Выпускает новый код регистрации; старый сразу перестаёт действовать.

        Raises:
            GroupNotFoundError: группы нет.
        """
        group = await self._get_group(group_id)
        code = self._security.issue_registration_code()
        group.registration_code_hash = self._security.hash_token(code)
        await self._uow.commit()
        return code

    async def add_invite(self, group_id: UUID, email: str) -> UUID:
        """Добавляет почту в список группы: по ней студент сможет зарегистрироваться.

        Raises:
            GroupNotFoundError: группы нет.
            InviteEmailTakenError: почта уже есть в списке этой или другой группы.
        """
        await self._get_group(group_id)
        invite = GroupInvite(id=uuid7(), group_id=group_id, email=email)
        self._uow.group_invites.add(invite)
        await self._commit_invite()
        return invite.id

    async def move_invite(self, invite_id: UUID, group_id: UUID) -> None:
        """Переносит почту в список другой группы. Уже зарегистрированного студента
        это не затрагивает: его группа меняется только переводом.

        Raises:
            InviteNotFoundError: почты нет ни в одном списке.
            GroupNotFoundError: группы нет.
        """
        invite = await self._uow.group_invites.get_by_id(invite_id)
        if invite is None:
            raise InviteNotFoundError({"invite_id": str(invite_id)})
        await self._get_group(group_id)
        invite.group_id = group_id
        await self._uow.commit()

    async def _apply_fields(self, group: Group, fields: GroupFields, name: str | None) -> None:
        """Записывает поля в группу; `name=None` — собрать название автоматически."""
        direction = await self._get_direction(fields.direction_id)
        group.direction_id = direction.id
        group.level = fields.level
        group.study_form = fields.study_form
        group.admission_year = fields.admission_year
        group.number = fields.number
        group.name = name or self._auto_name(
            direction, fields.level, fields.admission_year, fields.number
        )

    async def _get_direction(self, direction_id: UUID) -> Direction:
        direction = await self._uow.directions.get_by_id(direction_id)
        if direction is None:
            raise DirectionNotFoundError({"direction_id": str(direction_id)})
        return direction

    @staticmethod
    def _auto_name(
        direction: Direction, level: StudyLevel, admission_year: int, number: int
    ) -> str:
        """`Б` + `ВТ` + `26` + `01` = `БВТ2601`."""
        return f"{level.letter}{direction.short_name}{admission_year % 100:02d}{number:02d}"

    async def _get_group(self, group_id: UUID) -> Group:
        group = await self._uow.groups.get_by_id(group_id)
        if group is None:
            raise GroupNotFoundError({"group_id": str(group_id)})
        return group

    async def _commit_group(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_groups_name":
                raise GroupNameTakenError from exc
            raise

    async def _commit_invite(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_group_invites_email":
                raise InviteEmailTakenError from exc
            raise
