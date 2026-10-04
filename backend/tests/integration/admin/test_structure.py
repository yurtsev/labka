import logging
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient, Response
from prometheus_client import REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserRole
from src.core.db.models import Department, Direction, Faculty, User
from tests.support.admin import create_structure, form_error, signed_in_admin
from tests.support.auth import create_group


async def delete_error(client: AsyncClient, identity: str, pk: UUID) -> str | None:
    """Удаляет запись как кнопка в списке; возвращает текст ошибки, если она была."""
    response = await client.delete(f"/admin/{identity}/delete", params={"pks": str(pk)})
    assert response.status_code == 200, response.text
    return parse_qs(urlsplit(response.text).query).get("error", [None])[0]


@pytest.mark.case(id="ADMIN-STRUCTURE-001")
async def test_referenced_structure_is_not_deleted(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    db.add(
        User(
            id=uuid7(),
            last_name="Петров",
            first_name="Пётр",
            email="teacher@example.com",
            password_hash="hash",
            role=UserRole.TEACHER,
            department_id=structure.department_id,
        )
    )
    await db.commit()
    await signed_in_admin(client, db)

    assert await delete_error(client, "faculty", structure.faculty_id) == (
        "Нельзя удалить: к подразделению привязаны кафедры или направления"
    )
    assert await delete_error(client, "department", structure.department_id) == (
        "Нельзя удалить: на кафедре числятся преподаватели"
    )
    assert await delete_error(client, "direction", group.direction_id) == (
        "Нельзя удалить: у направления есть группы"
    )
    assert await db.get(Faculty, structure.faculty_id) is not None
    assert await db.get(Department, structure.department_id) is not None

    assert await delete_error(client, "direction", structure.direction_id) is None
    db.expunge_all()
    assert await db.get(Direction, structure.direction_id) is None


async def save_form(client: AsyncClient, url: str, **fields: str) -> Response:
    return await client.post(url, data={**fields, "save": "Save"})


@pytest.mark.case(id="ADMIN-STRUCTURE-002")
async def test_duplicate_structure_names_are_explained(
    client: AsyncClient, db: AsyncSession
) -> None:
    structure = await create_structure(db, direction="ВТ")
    other = await create_structure(db, direction="ПИ")
    await signed_in_admin(client, db)
    faculty = str(structure.faculty_id)

    faculty_twice = await save_form(
        client, "/admin/faculty/create", name="Факультет ВТ", short_name="ИТ", type="faculty"
    )
    faculty_renamed = await save_form(
        client,
        f"/admin/faculty/edit/{other.faculty_id}",
        name="Факультет ВТ",
        short_name="ИТ",
        type="faculty",
    )
    department_twice = await save_form(
        client, "/admin/department/create", faculty=faculty, name="Кафедра ВТ"
    )
    department_elsewhere = await save_form(
        client, "/admin/department/create", faculty=str(other.faculty_id), name="Кафедра ВТ"
    )
    direction_twice = await save_form(
        client, "/admin/direction/create", faculty=faculty, short_name="ПИ", name="Другое"
    )
    direction_renamed = await save_form(
        client,
        f"/admin/direction/edit/{structure.direction_id}",
        faculty=faculty,
        short_name="ПИ",
        name="Другое",
    )

    assert form_error(faculty_twice) == "Подразделение с таким названием уже есть"
    assert form_error(faculty_renamed) == "Подразделение с таким названием уже есть"
    assert form_error(department_twice) == "В этом подразделении уже есть кафедра с таким названием"
    assert department_elsewhere.status_code == 302, department_elsewhere.text
    assert form_error(direction_twice) == "Направление с таким сокращением уже есть"
    assert form_error(direction_renamed) == "Направление с таким сокращением уже есть"


@pytest.mark.case(id="ADMIN-STRUCTURE-003")
async def test_admin_form_error_is_reported(
    client: AsyncClient, db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    await create_structure(db, direction="ВТ")
    await signed_in_admin(client, db)
    labels = {
        "layer": "domain",
        "code": "admin.faculty_name_taken",
        "status": "400",
        "untranslated": "False",
    }
    before = REGISTRY.get_sample_value("app_errors_total", labels) or 0

    with caplog.at_level(logging.INFO):
        response = await save_form(
            client, "/admin/faculty/create", name="Факультет ВТ", short_name="ИТ", type="faculty"
        )

    assert response.status_code == 400
    [record] = [r for r in caplog.records if r.exc_info or r.getMessage() == "admin.error"]
    assert (record.getMessage(), record.levelno, record.exc_info) == (
        "admin.error",
        logging.INFO,
        None,
    )
    assert REGISTRY.get_sample_value("app_errors_total", labels) == before + 1
