import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import InvitedStudent, create_group, invite, register


@pytest.fixture
async def invited_student(db: AsyncSession) -> InvitedStudent:
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    await invite(db, group, "student@example.com")
    return InvitedStudent(
        group_id=group.id,
        group_code="GROUP-CODE-1",
        email="student@example.com",
        password="password-1",
    )


@pytest.fixture
async def registered_student(
    client: AsyncClient, invited_student: InvitedStudent
) -> InvitedStudent:
    """Зарегистрированный студент; cookie его первой сессии уже лежат в `client`."""
    response = await register(client, invited_student)
    assert response.status_code == 201, response.text
    return invited_student
