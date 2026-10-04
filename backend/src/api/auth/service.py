from datetime import UTC, datetime, timedelta
from uuid import uuid7

from src.api.auth.dto import IssuedTokens, Registration, SignedIn
from src.api.exc.auth import (
    AccountDeactivatedError,
    EmailAlreadyRegisteredError,
    EmailNotInvitedError,
    InvalidCredentialsError,
    InvalidGroupCodeError,
    InvalidRefreshTokenError,
    RefreshTokenReusedError,
    WrongCurrentPasswordError,
)
from src.config import cfg
from src.core.db.dto.user import UserDTO
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.user import User
from src.core.db.uow import UnitOfWork
from src.core.security.dto import AccessTokenClaims, CurrentUser
from src.core.security.exc import MalformedRefreshTokenError
from src.core.security.service import SecurityService, SessionIssuer


class AuthService:
    def __init__(
        self, uow: UnitOfWork, security: SecurityService, session_issuer: SessionIssuer
    ) -> None:
        self._uow = uow
        self._security = security
        self._session_issuer = session_issuer

    async def register(self, registration: Registration, user_agent: str | None) -> SignedIn:
        """Регистрирует студента по коду группы и сразу открывает сессию.

        Raises:
            InvalidGroupCodeError: кода нет или группа неактивна.
            EmailNotInvitedError: почты нет в списке этой группы.
            EmailAlreadyRegisteredError: почта уже использована.
        """
        code_hash = self._security.hash_token(registration.group_code)
        group = await self._uow.groups.get_by_registration_code_hash(code_hash)
        if group is None or not group.is_active:
            raise InvalidGroupCodeError

        invite = await self._uow.group_invites.get_by_email(registration.email)
        if invite is None or invite.group_id != group.id:
            raise EmailNotInvitedError({"group_id": str(group.id)})
        if invite.user_id is not None or await self._uow.users.get_by_email(registration.email):
            raise EmailAlreadyRegisteredError

        user = User(
            id=uuid7(),
            last_name=registration.last_name,
            first_name=registration.first_name,
            middle_name=registration.middle_name,
            email=registration.email,
            password_hash=self._security.hash_password(registration.password),
            role=UserRole.STUDENT,
            group_id=group.id,
        )
        try:
            self._uow.users.add(user)
            # Без relationship() порядок INSERT/UPDATE не гарантирован: пользователь должен
            # попасть в БД раньше, чем на него сошлётся приглашение.
            await self._uow.flush()
            invite.user_id = user.id
            tokens = self._open_session(user, user_agent)
            await self._uow.commit()
        except IntegrityViolationError as exc:
            # Параллельная регистрация той же почты: проверки выше её не видят.
            if exc.constraint in {"uq_users_email", "uq_group_invites_user_id"}:
                raise EmailAlreadyRegisteredError from exc
            raise
        return SignedIn(user=UserDTO.from_orm(user), tokens=tokens)

    async def login(self, email: str, password: str, user_agent: str | None) -> SignedIn:
        """Открывает сессию студента или преподавателя.

        Raises:
            InvalidCredentialsError: пользователя нет, пароль неверен или это админ.
            AccountDeactivatedError: пароль верен, но аккаунт деактивирован.
        """
        user = await self._uow.users.get_by_email(email)
        if (
            user is None
            or user.role == UserRole.ADMIN
            or not self._security.verify_password(user.password_hash, password)
        ):
            raise InvalidCredentialsError
        if not user.is_active:
            raise AccountDeactivatedError

        tokens = self._open_session(user, user_agent)
        await self._uow.commit()
        return SignedIn(user=UserDTO.from_orm(user), tokens=tokens)

    async def refresh(self, refresh_token: str | None) -> IssuedTokens:
        """Ротирует refresh-токен сессии и выдаёт новую пару токенов.

        Raises:
            InvalidRefreshTokenError: токена нет, он некорректен, сессия отозвана или истекла.
            RefreshTokenReusedError: пришёл уже заменённый токен — сессия отзывается.
            AccountDeactivatedError: пользователь деактивирован.
        """
        if not refresh_token:
            raise InvalidRefreshTokenError
        try:
            parsed = self._security.parse_refresh_token(refresh_token)
        except MalformedRefreshTokenError as exc:
            raise InvalidRefreshTokenError from exc

        now = datetime.now(UTC)
        session = await self._uow.sessions.get_for_update(parsed.session_id)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise InvalidRefreshTokenError
        if not self._security.verify_token(parsed.secret, session.refresh_token_hash):
            session.revoked_at = now
            await self._uow.commit()
            raise RefreshTokenReusedError({"session_id": str(session.id)})

        user = await self._uow.users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise AccountDeactivatedError

        new_refresh = self._security.issue_refresh_token(session.id)
        session.refresh_token_hash = self._security.hash_token(new_refresh.secret)
        session.expires_at = now + timedelta(days=cfg.auth.refresh_token_ttl_days)
        access_token = self._security.issue_access_token(
            AccessTokenClaims(user_id=user.id, session_id=session.id)
        )
        await self._uow.commit()
        return IssuedTokens(access_token=access_token, refresh_token=str(new_refresh))

    async def logout(self, refresh_token: str | None) -> None:
        """Отзывает сессию, к которой относится refresh-токен.

        Работает и с истёкшим access-токеном. Отсутствующий или битый токен — не ошибка:
        выход идемпотентен, cookie всё равно очищаются.
        """
        if not refresh_token:
            return
        try:
            parsed = self._security.parse_refresh_token(refresh_token)
        except MalformedRefreshTokenError:
            return
        session = await self._uow.sessions.get_for_update(parsed.session_id)
        if session is None or session.revoked_at is not None:
            return
        session.revoked_at = datetime.now(UTC)
        await self._uow.commit()

    async def change_password(
        self, current_user: CurrentUser, current_password: str, new_password: str
    ) -> None:
        """Меняет пароль и отзывает все сессии пользователя, кроме текущей.

        Raises:
            WrongCurrentPasswordError: текущий пароль неверен.
        """
        user = await self._get_user(current_user)
        if not self._security.verify_password(user.password_hash, current_password):
            raise WrongCurrentPasswordError

        user.password_hash = self._security.hash_password(new_password)
        await self._uow.sessions.revoke_all_for_user(
            user.id, datetime.now(UTC), except_session_id=current_user.session_id
        )
        await self._uow.commit()

    async def get_me(self, current_user: CurrentUser) -> UserDTO:
        return UserDTO.from_orm(await self._get_user(current_user))

    async def _get_user(self, current_user: CurrentUser) -> User:
        user = await self._uow.users.get_by_id(current_user.user_id)
        if user is None:
            raise InvalidCredentialsError
        return user

    def _open_session(self, user: User, user_agent: str | None) -> IssuedTokens:
        refresh_token = self._session_issuer.open(
            user.id, user_agent, timedelta(days=cfg.auth.refresh_token_ttl_days)
        )
        access_token = self._security.issue_access_token(
            AccessTokenClaims(user_id=user.id, session_id=refresh_token.session_id)
        )
        return IssuedTokens(access_token=access_token, refresh_token=str(refresh_token))
