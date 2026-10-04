import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import User
from tests.support.auth import InvitedStudent, create_admin, error_code, login


@pytest.mark.case(id="UC-C1-001")
async def test_login_opens_new_session(
    client: AsyncClient, registered_student: InvitedStudent
) -> None:
    client.cookies.clear()

    response = await login(client, registered_student.email.upper(), registered_student.password)

    assert response.status_code == 200
    assert response.json()["email"] == registered_student.email
    assert {"access_token", "refresh_token"} <= set(client.cookies.keys())
    assert (await client.get("/api/auth/me")).status_code == 200


@pytest.mark.case(id="UC-C1-002")
async def test_login_does_not_reveal_whether_email_exists(
    client: AsyncClient, registered_student: InvitedStudent
) -> None:
    wrong_password = await login(client, registered_student.email, "wrong-password")
    unknown_email = await login(client, "nobody@example.com", "wrong-password")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert error_code(wrong_password) == error_code(unknown_email) == "auth.invalid_credentials"


@pytest.mark.case(id="UC-C1-003")
async def test_login_reports_deactivated_account_only_after_correct_password(
    client: AsyncClient, db: AsyncSession, registered_student: InvitedStudent
) -> None:
    await db.execute(update(User).values(is_active=False))
    await db.commit()

    correct = await login(client, registered_student.email, registered_student.password)
    wrong = await login(client, registered_student.email, "wrong-password")

    assert correct.status_code == 401
    assert error_code(correct) == "auth.account_deactivated"
    assert error_code(wrong) == "auth.invalid_credentials"


@pytest.mark.case(id="UC-C1-004")
async def test_admin_cannot_sign_in_to_web_app(client: AsyncClient, db: AsyncSession) -> None:
    await create_admin(db, "admin@example.com", "admin-password")

    response = await login(client, "admin@example.com", "admin-password")

    assert response.status_code == 401
    assert error_code(response) == "auth.invalid_credentials"
