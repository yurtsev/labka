from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import GroupInvite, User
from tests.support.admin import form_error, signed_in_admin
from tests.support.auth import InvitedStudent, create_group, register


async def add_invite_form(client: AsyncClient, group_id: UUID, email: str) -> Response:
    return await client.post(
        "/admin/group-invite/create",
        data={"group": str(group_id), "email": email, "save": "Save"},
    )


@pytest.mark.case(id="ADMIN-INVITE-001")
async def test_invited_email_registers(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    await signed_in_admin(client, db)

    response = await add_invite_form(client, group.id, "  Student@Example.COM ")

    assert response.status_code == 302, response.text
    student = InvitedStudent(group.id, "GROUP-CODE-1", "student@example.com", "password-1")
    assert (await register(client, student)).status_code == 201
    invite = await db.scalar(select(GroupInvite).where(GroupInvite.email == student.email))
    assert invite is not None
    details = await client.get(f"/admin/group-invite/details/{invite.id}")
    assert "да" in details.text


@pytest.mark.case(id="ADMIN-INVITE-002")
async def test_duplicate_invite_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    first = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    second = await create_group(db, name="БВТ2602", code="GROUP-CODE-2")
    await signed_in_admin(client, db)
    assert (await add_invite_form(client, first.id, "student@example.com")).status_code == 302

    response = await add_invite_form(client, second.id, "student@example.com")

    assert response.status_code == 400
    assert form_error(response) == "Эта почта уже есть в списке одной из групп"


@pytest.mark.case(id="ADMIN-INVITE-003")
async def test_moved_invite_registers_into_new_group(client: AsyncClient, db: AsyncSession) -> None:
    old_group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    new_group = await create_group(db, name="БВТ2602", code="GROUP-CODE-2")
    await signed_in_admin(client, db)
    assert (await add_invite_form(client, old_group.id, "student@example.com")).status_code == 302
    invite = await db.scalar(select(GroupInvite).where(GroupInvite.email == "student@example.com"))
    assert invite is not None

    response = await client.post(
        f"/admin/group-invite/edit/{invite.id}",
        data={"group": str(new_group.id), "save": "Save"},
    )

    assert response.status_code == 302, response.text
    stale = InvitedStudent(old_group.id, "GROUP-CODE-1", "student@example.com", "password-1")
    assert (await register(client, stale)).status_code == 422
    fresh = InvitedStudent(new_group.id, "GROUP-CODE-2", "student@example.com", "password-1")
    assert (await register(client, fresh)).status_code == 201
    student = await db.scalar(select(User).where(User.email == "student@example.com"))
    assert student is not None and student.group_id == new_group.id
