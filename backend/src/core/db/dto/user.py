from dataclasses import dataclass
from uuid import UUID

from src.core.db.dto.base import BaseDTO
from src.core.db.enums import UserRole


@dataclass(frozen=True)
class UserDTO(BaseDTO):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    role: UserRole
