from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.config import cfg
from src.core.db.enums import UserRole
from src.core.db.models.session import Session
from src.core.db.uow import UnitOfWork
from src.core.security.exc import MalformedRefreshTokenError
from src.core.security.service import SecurityService, SessionIssuer


class AdminAuthService:
    """Вход в админку. Сессия админа — та же запись `Session`, что и в веб-приложении:
    отзыв сессий и деактивация действуют на неё так же."""

    def __init__(
        self, uow: UnitOfWork, security: SecurityService, session_issuer: SessionIssuer
    ) -> None:
        self._uow = uow
        self._security = security
        self._session_issuer = session_issuer

    async def login(self, email: str, password: str, user_agent: str | None) -> str | None:
        """Открывает сессию админа.

        Returns:
            Токен сессии `<session_id>.<secret>` для cookie или `None`, если пользователя нет,
            пароль неверен или вне допустимой длины, это не админ или аккаунт деактивирован.
        """
        if not cfg.auth.password_min_length <= len(password) <= cfg.auth.password_max_length:
            return None
        user = await self._uow.users.get_by_email(email)
        if (
            user is None
            or user.role != UserRole.ADMIN
            or not user.is_active
            or not self._security.verify_password(user.password_hash, password)
        ):
            return None

        token = self._session_issuer.open(
            user.id, user_agent, timedelta(hours=cfg.auth.admin_session_ttl_hours)
        )
        await self._uow.commit()
        return str(token)

    async def authenticate(self, token: str | None) -> UUID | None:
        """Возвращает id админа, если сессия жива, а пользователь — активный админ."""
        session = await self._get_valid_session(token)
        if session is None:
            return None
        user = await self._uow.users.get_by_id(session.user_id)
        if user is None or user.role != UserRole.ADMIN or not user.is_active:
            return None
        return user.id

    async def logout(self, token: str | None) -> None:
        """Отзывает сессию. Отсутствующий или недействительный токен — не ошибка."""
        session = await self._get_valid_session(token)
        if session is None:
            return
        session.revoked_at = datetime.now(UTC)
        await self._uow.commit()

    async def _get_valid_session(self, token: str | None) -> Session | None:
        if not token:
            return None
        try:
            parsed = self._security.parse_refresh_token(token)
        except MalformedRefreshTokenError:
            return None
        session = await self._uow.sessions.get_by_id(parsed.session_id)
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= datetime.now(UTC)
            or not self._security.verify_token(parsed.secret, session.refresh_token_hash)
        ):
            return None
        return session
