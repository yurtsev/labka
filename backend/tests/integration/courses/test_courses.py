import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import create_group, error_code
from tests.support.courses import (
    course_body,
    create_course,
    create_student,
    create_teacher,
    get_course,
    sign_in,
)


@pytest.mark.case(id="UC-T2-001")
async def test_teacher_creates_course(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    teacher_id = await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")

    course = await create_course(client, [group.id])

    assert course["name"] == "Алгоритмы"
    assert course["scale"] == {"type": "range", "min": 2, "max": 5}
    assert course["grading_note"] == "Оценка = код + защита"
    assert course["teacher"]["id"] == str(teacher_id)
    assert course["groups"] == [{"id": str(group.id), "name": "БВТ2601"}]
    assert course["is_archived"] is False
    assert (await get_course(client, course["id"])).json() == course


@pytest.mark.case(id="UC-T2-002")
async def test_course_requires_attached_active_groups(
    client: AsyncClient, db: AsyncSession
) -> None:
    attached = await create_group(db, name="БВТ2601", code="CODE-1")
    inactive = await create_group(db, name="БВТ2602", code="CODE-2", is_active=False)
    foreign = await create_group(db, name="БВТ2603", code="CODE-3")
    await create_teacher(db, "teacher@example.com", "password-1", [attached, inactive])
    await sign_in(client, "teacher@example.com", "password-1")

    for group in (inactive, foreign):
        response = await client.post("/api/courses", json=course_body([attached.id, group.id]))
        assert response.status_code == 422
        assert error_code(response) == "courses.group_not_available"
    assert (await client.get("/api/courses")).json()["items"] == []


@pytest.mark.case(id="UC-T2-003")
async def test_student_cannot_create_course(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "student@example.com")

    created = await client.post("/api/courses", json=course_body([group.id]))
    groups = await client.get("/api/courses/available-groups")

    assert created.status_code == 403
    assert error_code(created) == "courses.teacher_only"
    assert groups.status_code == 403


@pytest.mark.case(id="UC-T2-004")
async def test_invalid_scale_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")

    for scale in (
        {"type": "range", "min": 5, "max": 5},
        {"type": "range", "min": 2},
        {"type": "binary", "min": 0, "max": 1},
        {"type": "percent"},
    ):
        response = await client.post("/api/courses", json=course_body([group.id], scale=scale))
        assert response.status_code == 422, scale

    no_groups = await client.post("/api/courses", json=course_body([]))
    assert no_groups.status_code == 422

    binary = await create_course(client, [group.id], scale={"type": "binary"})
    assert binary["scale"] == {"type": "binary", "min": None, "max": None}


@pytest.mark.case(id="UC-T3-001")
async def test_teacher_updates_own_course_only(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_teacher(db, "other@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id])
    update = {
        "name": "Алгоритмы 2",
        "description": "",
        "scale": {"type": "binary"},
        "grading_note": "Зачёт за все лабы",
    }

    response = await client.put(f"/api/courses/{course['id']}", json=update)

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Алгоритмы 2"
    assert updated["description"] is None
    assert updated["scale"] == {"type": "binary", "min": None, "max": None}
    assert updated["groups"] == course["groups"]

    await sign_in(client, "other@example.com", "password-1")
    foreign = await client.put(f"/api/courses/{course['id']}", json=update)
    assert foreign.status_code == 403
    assert error_code(foreign) == "courses.forbidden"
    assert (await get_course(client, course["id"])).status_code == 403
    missing = await get_course(client, "01900000-0000-7000-8000-000000000000")
    assert missing.status_code == 404
    assert error_code(missing) == "courses.not_found"
