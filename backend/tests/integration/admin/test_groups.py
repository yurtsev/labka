from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Group
from tests.support.admin import (
    create_structure,
    form_error,
    revealed_secret,
    signed_in_admin,
)
from tests.support.auth import InvitedStudent, invite, register


async def create_group_form(client: AsyncClient, direction_id: UUID, **fields: str) -> Response:
    form = {
        "direction": str(direction_id),
        "level": "bachelor",
        "study_form": "full_time",
        "admission_year": "2026",
        "number": "1",
        "name": "",
        "save": "Save",
        **fields,
    }
    return await client.post("/admin/group/create", data=form)


async def edit_group_form(
    client: AsyncClient, group: Group, direction_id: UUID, **fields: str
) -> Response:
    form = {
        "direction": str(direction_id),
        "level": group.level.value,
        "study_form": group.study_form.value,
        "admission_year": str(group.admission_year),
        "number": str(group.number),
        "name": group.name,
        "save": "Save",
        **fields,
    }
    return await client.post(f"/admin/group/edit/{group.id}", data=form)


async def group_by_name(db: AsyncSession, name: str) -> Group:
    group = await db.scalar(select(Group).where(Group.name == name))
    assert group is not None
    return group


@pytest.mark.case(id="ADMIN-GROUP-001")
async def test_group_gets_auto_name_and_one_time_code(
    client: AsyncClient, db: AsyncSession
) -> None:
    structure = await create_structure(db, direction="ВТ")
    await signed_in_admin(client, db)

    response = await create_group_form(client, structure.direction_id, number="3")

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"].startswith("no-store")
    code = revealed_secret(response)
    group = await group_by_name(db, "БВТ2603")
    assert group.registration_code_hash != code
    await invite(db, group, "student@example.com")
    student = InvitedStudent(group.id, code, "student@example.com", "password-1")
    assert (await register(client, student)).status_code == 201


@pytest.mark.case(id="ADMIN-GROUP-002")
async def test_manual_group_name_is_kept(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    await signed_in_admin(client, db)

    response = await create_group_form(client, structure.direction_id, name="М092401(71)")

    assert response.status_code == 200, response.text
    await group_by_name(db, "М092401(71)")


@pytest.mark.case(id="ADMIN-GROUP-003")
async def test_duplicate_group_name_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    await signed_in_admin(client, db)
    assert (await create_group_form(client, structure.direction_id)).status_code == 200

    response = await create_group_form(client, structure.direction_id, name="БВТ2601")

    assert response.status_code == 400
    assert form_error(response) == "Группа с таким названием уже есть"
    assert await db.scalar(select(func.count(Group.id))) == 1


@pytest.mark.case(id="ADMIN-GROUP-004")
async def test_reissued_code_replaces_old_one(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    await signed_in_admin(client, db)
    old_code = revealed_secret(await create_group_form(client, structure.direction_id))
    group = await group_by_name(db, "БВТ2601")
    await invite(db, group, "student@example.com")

    response = await client.get("/admin/group/action/reissue-code", params={"pks": str(group.id)})

    assert response.status_code == 200, response.text
    new_code = revealed_secret(response)
    assert new_code != old_code
    stale = InvitedStudent(group.id, old_code, "student@example.com", "password-1")
    assert (await register(client, stale)).status_code == 422
    fresh = InvitedStudent(group.id, new_code, "student@example.com", "password-1")
    assert (await register(client, fresh)).status_code == 201


@pytest.mark.case(id="ADMIN-GROUP-005")
async def test_group_edit_rebuilds_untouched_auto_name(
    client: AsyncClient, db: AsyncSession
) -> None:
    structure = await create_structure(db)
    await signed_in_admin(client, db)
    await create_group_form(client, structure.direction_id)
    await create_group_form(client, structure.direction_id, number="2", name="М092401(71)")
    auto = await group_by_name(db, "БВТ2601")
    manual = await group_by_name(db, "М092401(71)")

    auto_edit = await edit_group_form(client, auto, structure.direction_id, number="5")
    manual_edit = await edit_group_form(client, manual, structure.direction_id, number="7")

    assert auto_edit.status_code == 302, auto_edit.text
    assert manual_edit.status_code == 302, manual_edit.text
    db.expire_all()
    assert (await group_by_name(db, "БВТ2605")).number == 5
    assert (await group_by_name(db, "М092401(71)")).number == 7
