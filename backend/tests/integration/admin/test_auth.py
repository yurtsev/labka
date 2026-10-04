import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import User
from tests.support.admin import admin_login, signed_in_admin
from tests.support.auth import InvitedStudent, create_admin, create_group, invite, register


@pytest.mark.case(id="ADMIN-AUTH-001")
async def test_admin_requires_login(client: AsyncClient, db: AsyncSession) -> None:
    anonymous = await client.get("/admin/")
    assert anonymous.status_code == 302
    assert anonymous.headers["location"].endswith("/admin/login")
    assert "Вход" in (await client.get("/admin/login")).text

    await signed_in_admin(client, db)
    signed_in = await client.get("/admin/")

    assert signed_in.status_code == 200


@pytest.mark.case(id="ADMIN-AUTH-002")
async def test_non_admin_cannot_sign_in(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    await invite(db, group, "student@example.com")
    student = InvitedStudent(group.id, "GROUP-CODE-1", "student@example.com", "password-1")
    assert (await register(client, student)).status_code == 201

    response = await admin_login(client, student.email, student.password)

    assert response.status_code == 400
    assert "Неверная почта или пароль" in response.text
    assert "Invalid credentials" not in response.text
    assert "admin_session" not in response.cookies
    assert (await client.get("/admin/")).status_code == 302


@pytest.mark.case(id="ADMIN-AUTH-003")
async def test_logout_revokes_admin_session(client: AsyncClient, db: AsyncSession) -> None:
    await signed_in_admin(client, db)
    session_cookie = client.cookies["admin_session"]

    await client.get("/admin/logout")
    client.cookies.set("admin_session", session_cookie, path="/admin/")

    assert (await client.get("/admin/")).status_code == 302


@pytest.mark.case(id="ADMIN-AUTH-004")
async def test_deactivated_admin_loses_access(client: AsyncClient, db: AsyncSession) -> None:
    await signed_in_admin(client, db, email="admin@example.com")

    await db.execute(update(User).where(User.email == "admin@example.com").values(is_active=False))
    await db.commit()

    assert (await client.get("/admin/")).status_code == 302


@pytest.mark.case(id="ADMIN-AUTH-005")
async def test_too_long_admin_password_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    too_long = "x" * 33
    await create_admin(db, "admin@example.com", too_long)

    response = await admin_login(client, "admin@example.com", too_long)

    assert response.status_code == 400
    assert "admin_session" not in response.cookies
