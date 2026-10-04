import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from src.config import cfg
from src.core.db.models.session import Session
from src.core.db.uow import UnitOfWork
from src.core.security.dto import AccessTokenClaims, CurrentUser, RefreshToken
from src.core.security.exc import (
    MalformedRefreshTokenError,
    NotAuthenticatedError,
)


class SecurityService:
    """Криптография аутентификации: пароли, access-JWT и непрозрачные токены."""

    def __init__(self) -> None:
        self._password_hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self._password_hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self._password_hasher.verify(password_hash, password)
        except VerificationError, InvalidHashError:
            return False

    def issue_access_token(self, claims: AccessTokenClaims) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(claims.user_id),
            "sid": str(claims.session_id),
            "iat": now,
            "exp": now + timedelta(minutes=cfg.auth.access_token_ttl_minutes),
        }
        return jwt.encode(payload, cfg.auth.jwt_secret, algorithm="HS256")

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        """Проверяет подпись и срок access-токена.

        Raises:
            NotAuthenticatedError: подпись или срок недействительны, формат claims неверен.
        """
        try:
            payload = jwt.decode(
                token,
                cfg.auth.jwt_secret,
                algorithms=["HS256"],
                options={"require": ["sub", "sid", "exp"]},
            )
            return AccessTokenClaims(user_id=UUID(payload["sub"]), session_id=UUID(payload["sid"]))
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise NotAuthenticatedError from exc

    def generate_password(self) -> str:
        """Случайный пароль, который админ один раз показывает пользователю."""
        return secrets.token_urlsafe(12)

    def issue_registration_code(self) -> str:
        """Код регистрации группы без похожих символов (0/O, 1/I): его диктуют старосте."""
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(secrets.choice(alphabet) for _ in range(10))

    def issue_refresh_token(self, session_id: UUID) -> RefreshToken:
        return RefreshToken(session_id=session_id, secret=secrets.token_urlsafe(32))

    def parse_refresh_token(self, token: str) -> RefreshToken:
        """Разбирает refresh-токен `<session_id>.<secret>` без обращения к БД.

        Raises:
            MalformedRefreshTokenError: строка не соответствует формату.
        """
        session_part, _, secret = token.partition(".")
        try:
            session_id = UUID(session_part)
        except ValueError as exc:
            raise MalformedRefreshTokenError from exc
        if not secret:
            raise MalformedRefreshTokenError
        return RefreshToken(session_id=session_id, secret=secret)

    def hash_token(self, value: str) -> str:
        """SHA-256 для высокоэнтропийных значений (refresh-секрет, код группы).

        Детерминированный хэш позволяет искать запись по значению; для паролей не подходит.
        """
        return hashlib.sha256(value.encode()).hexdigest()

    def verify_token(self, value: str, token_hash: str) -> bool:
        return hmac.compare_digest(self.hash_token(value), token_hash)


class SessionAuthenticator:
    """Определяет текущего пользователя по access-токену и списку разрешённых сессий."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    async def authenticate(self, access_token: str | None) -> CurrentUser:
        """Проверяет токен, что сессия не отозвана и не истекла, а пользователь активен.

        Raises:
            NotAuthenticatedError: токена нет или любая из проверок не прошла.
        """
        if not access_token:
            raise NotAuthenticatedError
        claims = self._security.decode_access_token(access_token)
        user = await self._uow.users.get_by_active_session(claims.session_id, datetime.now(UTC))
        if user is None or user.id != claims.user_id:
            raise NotAuthenticatedError
        return CurrentUser(user_id=user.id, session_id=claims.session_id, role=user.role)


class SessionIssuer:
    """Открывает сессии — записи в списке разрешённых сессий — для любого входа."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    def open(self, user_id: UUID, user_agent: str | None, ttl: timedelta) -> RefreshToken:
        """Добавляет сессию в UoW; commit делает вызывающий сервис.

        Returns:
            Токен `<session_id>.<secret>`: в БД остаётся только хэш секрета.
        """
        token = self._security.issue_refresh_token(uuid7())
        self._uow.sessions.add(
            Session(
                id=token.session_id,
                user_id=user_id,
                refresh_token_hash=self._security.hash_token(token.secret),
                expires_at=datetime.now(UTC) + ttl,
                user_agent=user_agent,
            )
        )
        return token
