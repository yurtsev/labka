import re
from dataclasses import dataclass
from uuid import UUID, uuid7

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import FacultyType
from src.core.db.models import Department, Direction, Faculty
from tests.support.auth import create_admin


@dataclass(frozen=True)
class Structure:
    faculty_id: UUID
    department_id: UUID
    direction_id: UUID


async def create_structure(db: AsyncSession, direction: str = "ВТ") -> Structure:
    faculty = Faculty(
        id=uuid7(), name=f"Факультет {direction}", short_name="ИТ", type=FacultyType.FACULTY
    )
    db.add(faculty)
    await db.flush()
    department = Department(id=uuid7(), faculty_id=faculty.id, name=f"Кафедра {direction}")
    direction_row = Direction(
        id=uuid7(), faculty_id=faculty.id, short_name=direction, name="Вычислительная техника"
    )
    db.add_all([department, direction_row])
    await db.commit()
    return Structure(
        faculty_id=faculty.id, department_id=department.id, direction_id=direction_row.id
    )


async def admin_login(client: AsyncClient, email: str, password: str) -> Response:
    return await client.post("/admin/login", data={"username": email, "password": password})


async def signed_in_admin(
    client: AsyncClient,
    db: AsyncSession,
    email: str = "admin@example.com",
    password: str = "admin-password-1",
) -> None:
    await create_admin(db, email, password)
    response = await admin_login(client, email, password)
    assert response.status_code == 302, response.text


def revealed_secret(response: Response) -> str:
    """Значение из окна «показать один раз» на странице sqladmin."""
    match = re.search(r'value="([^"]+)" readonly id="modal-secret-value"', response.text)
    assert match is not None, "на странице нет одноразового секрета"
    return match.group(1)


def form_error(response: Response) -> str:
    match = re.search(r'<div class="alert alert-danger" role="alert">(.*?)</div>', response.text)
    assert match is not None, "на странице нет ошибки формы"
    return match.group(1)
