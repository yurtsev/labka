from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import UserRole


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID


@dataclass(frozen=True)
class RefreshToken:
    """Refresh-токен вида `<session_id>.<secret>`; в БД хранится только хэш `secret`."""

    session_id: UUID
    secret: str

    def __str__(self) -> str:
        return f"{self.session_id}.{self.secret}"


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    session_id: UUID
    role: UserRole
