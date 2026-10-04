import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserRole
from src.core.db.models import GroupInvite, User
from tests.support.auth import InvitedStudent, create_group, error_code, invite, register


@pytest.mark.case(id="UC-C0-001")
async def test_registration_creates_student_in_group_and_signs_in(
    client: AsyncClient, db: AsyncSession, invited_student: InvitedStudent
) -> None:
    response = await register(client, invited_student)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == invited_student.email
    assert body["role"] == UserRole.STUDENT
    user = await db.scalar(select(User).where(User.email == invited_student.email))
    assert user is not None
    assert user.group_id == invited_student.group_id
    assert user.password_hash != invited_student.password
    invite_row = await db.scalar(select(GroupInvite).where(GroupInvite.email == user.email))
    assert invite_row is not None and invite_row.user_id == user.id
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)


@pytest.mark.case(id="UC-C0-002")
async def test_registration_rejects_wrong_group_code(
    client: AsyncClient, db: AsyncSession, invited_student: InvitedStudent
) -> None:
    response = await register(client, invited_student, group_code="WRONG-CODE")

    assert response.status_code == 422
    assert error_code(response) == "auth.invalid_group_code"
    assert await db.scalar(select(User)) is None


@pytest.mark.case(id="UC-C0-003")
async def test_registration_rejects_code_of_inactive_group(
    client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2602", code="INACTIVE-CODE", is_active=False)
    await invite(db, group, "late@example.com")
    student = InvitedStudent(group.id, "INACTIVE-CODE", "late@example.com", "password-1")

    response = await register(client, student)

    assert response.status_code == 422
    assert error_code(response) == "auth.invalid_group_code"


@pytest.mark.case(id="UC-C0-004")
async def test_registration_rejects_email_missing_from_this_group_list(
    client: AsyncClient, db: AsyncSession, invited_student: InvitedStudent
) -> None:
    other_group = await create_group(db, name="БВТ2603", code="OTHER-CODE")
    await invite(db, other_group, "other@example.com")

    not_listed = await register(client, invited_student, email="stranger@example.com")
    listed_elsewhere = await register(client, invited_student, email="other@example.com")

    assert not_listed.status_code == listed_elsewhere.status_code == 422
    assert error_code(not_listed) == error_code(listed_elsewhere) == "auth.email_not_invited"


@pytest.mark.case(id="UC-C0-005")
async def test_registration_rejects_already_used_email(
    client: AsyncClient, registered_student: InvitedStudent
) -> None:
    response = await register(client, registered_student)

    assert response.status_code == 409
    assert error_code(response) == "auth.email_already_registered"


@pytest.mark.case(id="UC-C0-006")
async def test_registration_normalizes_email_case_and_name_whitespace(
    client: AsyncClient, invited_student: InvitedStudent
) -> None:
    response = await register(
        client,
        invited_student,
        email=invited_student.email.upper(),
        group_code=f"  {invited_student.group_code} ",
        last_name="  Петров ",
    )

    assert response.status_code == 201
    assert response.json()["email"] == invited_student.email
    assert response.json()["last_name"] == "Петров"


@pytest.mark.case(id="UC-C0-007")
@pytest.mark.parametrize("password", ["short", "x" * 33])
async def test_registration_rejects_password_out_of_length(
    client: AsyncClient, invited_student: InvitedStudent, password: str
) -> None:
    response = await register(client, invited_student, password=password)

    assert response.status_code == 422
    assert error_code(response) == "request.invalid"
