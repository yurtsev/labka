from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid7

from email_validator import EmailNotValidError, validate_email

from src.admin.exc.groups import (
    BatchSizeError,
    DirectionNotFoundError,
    GroupNamesTakenError,
    GroupNameTakenError,
    GroupNotFoundError,
    InviteEmailTakenError,
    InviteNotFoundError,
)
from src.admin.groups.dto import (
    BatchFields,
    CreatedBatchGroup,
    CreatedGroup,
    GroupFields,
    InviteImport,
)
from src.config import cfg
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

    async def create_batch(self, fields: BatchFields) -> list[CreatedBatchGroup]:
        """Создаёт группы `БВТ2601…БВТ260N` и каждой выпускает код регистрации.

        Либо создаются все, либо ни одной: если какое-то название занято, ничего не меняется.

        Returns:
            Названия и коды в открытом виде: показать коды можно только сейчас.

        Raises:
            BatchSizeError: количество вне границ.
            DirectionNotFoundError: направления нет.
            GroupNamesTakenError: хотя бы одно из названий уже занято.
        """
        if not 1 <= fields.count <= cfg.administration.max_batch_groups:
            raise BatchSizeError({"max": cfg.administration.max_batch_groups})
        direction = await self._get_direction(fields.direction_id)
        names = [
            self._auto_name(direction, fields.level, fields.admission_year, number)
            for number in range(1, fields.count + 1)
        ]
        taken = await self._uow.groups.names_taken(names)
        if taken:
            raise GroupNamesTakenError({"names": taken})
        created = []
        for number, name in enumerate(names, start=1):
            code = self._security.issue_registration_code()
            self._uow.groups.add(
                Group(
                    id=uuid7(),
                    direction_id=direction.id,
                    level=fields.level,
                    study_form=fields.study_form,
                    admission_year=fields.admission_year,
                    number=number,
                    name=name,
                    registration_code_hash=self._security.hash_token(code),
                )
            )
            created.append(CreatedBatchGroup(name=name, registration_code=code))
        await self._commit_group()
        return created

    async def set_active(
        self, group_ids: Sequence[UUID], active: bool, *, with_students: bool = False
    ) -> int:
        """Деактивирует или возвращает группы; по желанию вместе с их студентами.

        Неактивную группу нельзя добавить в курс, по её коду нельзя зарегистрироваться.
        Деактивированные студенты не могут войти, их сессии завершаются; вернуть студентов
        в работу админ может отдельно.

        Returns:
            Сколько групп изменено.

        Raises:
            GroupNotFoundError: ни одной из выбранных групп нет.
        """
        groups = await self._uow.groups.get_many(group_ids)
        if not groups:
            raise GroupNotFoundError({"group_ids": [str(item) for item in group_ids]})
        for group in groups:
            group.is_active = active
        if with_students and not active:
            student_ids = await self._uow.users.deactivate_students_of_groups(
                [group.id for group in groups]
            )
            await self._uow.sessions.revoke_all_for_users(student_ids, datetime.now(UTC))
        await self._uow.commit()
        return len(groups)

    async def import_invites(self, group_id: UUID, tokens: Sequence[str]) -> InviteImport:
        """Добавляет почты в список группы и отдельно называет те, что не добавлены.

        Raises:
            GroupNotFoundError: группы нет.
        """
        await self._get_group(group_id)
        valid: list[str] = []
        invalid: list[str] = []
        repeated: list[str] = []
        for token in tokens:
            email = self._normalize_email(token)
            if email is None:
                invalid.append(token)
            elif email in valid:
                repeated.append(email)
            else:
                valid.append(email)
        added = await self._uow.group_invites.add_new([(group_id, email) for email in valid])
        await self._uow.commit()
        return InviteImport(
            added=tuple(email for email in valid if email in added),
            invalid=tuple(invalid),
            repeated=tuple(repeated),
            already_listed=tuple(email for email in valid if email not in added),
        )

    async def list_directions(self) -> list[Direction]:
        return await self._uow.directions.list_all()

    async def list_groups(self) -> list[Group]:
        return await self._uow.groups.list_all()

    async def list_active_groups(self) -> list[Group]:
        return await self._uow.groups.list_active()

    async def get_group_name(self, group_id: UUID) -> str:
        """Название группы.

        Raises:
            GroupNotFoundError: группы нет.
        """
        return (await self._get_group(group_id)).name

    @staticmethod
    def _normalize_email(token: str) -> str | None:
        try:
            return validate_email(token.strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            return None

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
