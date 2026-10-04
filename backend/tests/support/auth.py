import hashlib
from dataclasses import dataclass
from uuid import UUID, uuid7

from argon2 import PasswordHasher
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import FacultyType, StudyForm, StudyLevel, UserRole
from src.core.db.models import Direction, Faculty, Group, GroupInvite, User


@dataclass(frozen=True)
class InvitedStudent:
    group_id: UUID
    group_code: str
    email: str
    password: str


async def create_group(db: AsyncSession, *, name: str, code: str, is_active: bool = True) -> Group:
    faculty = Faculty(
        id=uuid7(), name=f"Факультет {name}", short_name="ИТ", type=FacultyType.FACULTY
    )
    direction = Direction(
        id=uuid7(), faculty_id=faculty.id, short_name=name, name=f"Направление {name}"
    )
    group = Group(
        id=uuid7(),
        direction_id=direction.id,
        level=StudyLevel.BACHELOR,
        study_form=StudyForm.FULL_TIME,
        admission_year=2026,
        number=1,
        name=name,
        registration_code_hash=hashlib.sha256(code.encode()).hexdigest(),
        is_active=is_active,
    )
    db.add(faculty)
    await db.flush()
    db.add(direction)
    await db.flush()
    db.add(group)
    await db.commit()
    return group


async def invite(db: AsyncSession, group: Group, email: str) -> None:
    db.add(GroupInvite(id=uuid7(), group_id=group.id, email=email))
    await db.commit()


async def create_admin(db: AsyncSession, email: str, password: str) -> None:
    db.add(
        User(
            id=uuid7(),
            last_name="Админов",
            first_name="Админ",
            email=email,
            password_hash=PasswordHasher().hash(password),
            role=UserRole.ADMIN,
        )
    )
    await db.commit()


async def register(client: AsyncClient, student: InvitedStudent, **overrides: str) -> Response:
    body = {
        "email": student.email,
        "group_code": student.group_code,
        "last_name": "Иванов",
        "first_name": "Иван",
        "middle_name": "Иванович",
        "password": student.password,
        **overrides,
    }
    return await client.post("/api/auth/register", json=body)


async def login(client: AsyncClient, email: str, password: str) -> Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


def error_code(response: Response) -> str:
    return response.json()["error"]["code"]
