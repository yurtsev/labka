from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserRole
from src.core.db.models import Group, TeacherGroup, User
from tests.support.admin import create_structure, form_error, revealed_secret, signed_in_admin
from tests.support.auth import create_group, login


def teacher_form(department_id: UUID, group_ids: list[UUID], **fields: str) -> dict[str, object]:
    return {
        "last_name": "Петров",
        "first_name": "Пётр",
        "middle_name": "",
        "email": "teacher@example.com",
        "department": str(department_id),
        "teaching_groups": [str(group_id) for group_id in group_ids],
        "save": "Save",
        **fields,
    }


async def create_teacher_form(client: AsyncClient, form: dict[str, object]) -> Response:
    return await client.post("/admin/teacher/create", data=form)


async def teacher_groups(db: AsyncSession, email: str) -> set[UUID]:
    query = (
        select(TeacherGroup.group_id)
        .join(User, User.id == TeacherGroup.teacher_id)
        .where(User.email == email)
    )
    return set(await db.scalars(query))


@pytest.mark.case(id="ADMIN-TEACHER-001")
async def test_teacher_signs_in_with_generated_password(
    client: AsyncClient, db: AsyncSession
) -> None:
    structure = await create_structure(db)
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    await signed_in_admin(client, db)

    response = await create_teacher_form(
        client, teacher_form(structure.department_id, [group.id], email=" Teacher@Example.com")
    )

    assert response.status_code == 200, response.text
    assert "Скопировать" in response.text
    password = revealed_secret(response)
    signed_in = await login(client, "teacher@example.com", password)
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["role"] == UserRole.TEACHER
    assert await teacher_groups(db, "teacher@example.com") == {group.id}


@pytest.mark.case(id="ADMIN-TEACHER-002")
async def test_teacher_groups_are_replaced(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    first = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    second = await create_group(db, name="БВТ2602", code="GROUP-CODE-2")
    await signed_in_admin(client, db)
    form = teacher_form(structure.department_id, [first.id])
    assert (await create_teacher_form(client, form)).status_code == 200
    teacher = await db.scalar(select(User).where(User.email == "teacher@example.com"))
    assert teacher is not None

    response = await client.post(
        f"/admin/teacher/edit/{teacher.id}",
        data=teacher_form(structure.department_id, [second.id], last_name="Сидоров"),
    )

    assert response.status_code == 302, response.text
    assert await teacher_groups(db, "teacher@example.com") == {second.id}
    await db.refresh(teacher)
    assert teacher.last_name == "Сидоров"


@pytest.mark.case(id="ADMIN-TEACHER-003")
async def test_duplicate_teacher_email_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    await signed_in_admin(client, db)

    response = await create_teacher_form(
        client, teacher_form(structure.department_id, [], email="admin@example.com")
    )

    assert response.status_code == 400
    assert form_error(response) == "Пользователь с этой почтой уже есть"


@pytest.mark.case(id="ADMIN-TEACHER-004")
async def test_teacher_section_hides_other_users(client: AsyncClient, db: AsyncSession) -> None:
    await signed_in_admin(client, db)
    admin = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    assert admin is not None

    listing = await client.get("/admin/teacher/list")
    details = await client.get(f"/admin/teacher/details/{admin.id}")
    edit = await client.get(f"/admin/teacher/edit/{admin.id}")

    assert listing.status_code == 200
    assert "admin@example.com" not in listing.text
    assert details.status_code == 404
    assert edit.status_code == 404


@pytest.mark.case(id="ADMIN-TEACHER-005")
async def test_inactive_group_is_not_attached(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    active = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    inactive = await create_group(db, name="БВТ2602", code="GROUP-CODE-2", is_active=False)
    await signed_in_admin(client, db)

    rejected = await create_teacher_form(
        client, teacher_form(structure.department_id, [active.id, inactive.id])
    )
    assert rejected.status_code == 400
    assert form_error(rejected) == "Нельзя прикрепить неактивную группу"

    assert (
        await create_teacher_form(client, teacher_form(structure.department_id, [active.id]))
    ).status_code == 200
    teacher = await db.scalar(select(User).where(User.email == "teacher@example.com"))
    assert teacher is not None
    await db.execute(update(Group).where(Group.id == active.id).values(is_active=False))
    await db.commit()

    kept = await client.post(
        f"/admin/teacher/edit/{teacher.id}",
        data=teacher_form(structure.department_id, [active.id], last_name="Сидоров"),
    )
    assert kept.status_code == 302, kept.text
    assert await teacher_groups(db, "teacher@example.com") == {active.id}
