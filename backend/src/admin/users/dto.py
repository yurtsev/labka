from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ResetPassword:
    """Новый пароль пользователя: показать его можно только сейчас."""

    user_id: UUID
    full_name: str
    email: str
    password: str


@dataclass(frozen=True)
class StudentRef:
    id: UUID
    full_name: str
    group_name: str
