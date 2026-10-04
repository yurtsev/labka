from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from src.config import cfg
from src.core.db.enums import UserRole

type NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]
type PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type Password = Annotated[
    str,
    Field(min_length=cfg.auth.password_min_length, max_length=cfg.auth.password_max_length),
]


class RegisterRequest(BaseModel):
    email: NormalizedEmail
    group_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    last_name: PersonName
    first_name: PersonName
    middle_name: PersonName | None = None
    password: Password


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: Password


class PasswordChangeRequest(BaseModel):
    current_password: Password
    new_password: Password


class UserResponse(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    role: UserRole
