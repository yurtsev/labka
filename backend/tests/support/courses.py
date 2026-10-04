from uuid import UUID, uuid7

from argon2 import PasswordHasher
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserRole
from src.core.db.models import Group, TeacherGroup, User
from tests.support.admin import create_structure
from tests.support.auth import InvitedStudent, invite, login, register


async def create_teacher(db: AsyncSession, email: str, password: str, groups: list[Group]) -> UUID:
    structure = await create_structure(db, direction=f"Т{email[:6]}")
    teacher = User(
        id=uuid7(),
        last_name="Петров",
        first_name="Пётр",
        middle_name="Петрович",
        email=email,
        password_hash=PasswordHasher().hash(password),
        role=UserRole.TEACHER,
        department_id=structure.department_id,
    )
    db.add(teacher)
    await db.flush()
    db.add_all(TeacherGroup(teacher_id=teacher.id, group_id=group.id) for group in groups)
    await db.commit()
    return teacher.id


async def sign_in(client: AsyncClient, email: str, password: str) -> None:
    response = await login(client, email, password)
    assert response.status_code == 200, response.text


async def create_student(
    client: AsyncClient, db: AsyncSession, group: Group, code: str, email: str
) -> InvitedStudent:
    """Регистрирует студента; cookie его сессии остаются в `client`."""
    await invite(db, group, email)
    student = InvitedStudent(group.id, code, email, "password-1")
    response = await register(client, student)
    assert response.status_code == 201, response.text
    return student


def course_body(group_ids: list[UUID], **fields: object) -> dict[str, object]:
    return {
        "name": "Алгоритмы",
        "description": "Сортировки и графы",
        "scale": {"type": "range", "min": 2, "max": 5},
        "grading_note": "Оценка = код + защита",
        "group_ids": [str(group_id) for group_id in group_ids],
        **fields,
    }


async def create_course(client: AsyncClient, group_ids: list[UUID], **fields: object) -> dict:
    response = await client.post("/api/courses", json=course_body(group_ids, **fields))
    assert response.status_code == 201, response.text
    body: dict = response.json()
    return body


async def get_course(client: AsyncClient, course_id: str) -> Response:
    return await client.get(f"/api/courses/{course_id}")
