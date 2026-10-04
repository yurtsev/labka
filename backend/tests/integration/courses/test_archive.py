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


@pytest.mark.case(id="UC-T15-001")
async def test_archived_course_is_read_only(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id])
    course_url = f"/api/courses/{course['id']}"

    archived = await client.post(f"{course_url}/archive")

    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert (await client.get("/api/courses")).json()["items"] == []
    assert [c["id"] for c in (await client.get("/api/courses?archived=true")).json()["items"]] == [
        course["id"]
    ]
    update = await client.put(course_url, json=course_body([]))
    remove = await client.delete(f"{course_url}/groups/{group.id}")
    assert (update.status_code, error_code(update)) == (409, "courses.archived")
    assert (remove.status_code, error_code(remove)) == (409, "courses.archived")

    await sign_in(client, "student@example.com", "password-1")
    assert (await client.get("/api/courses")).json()["items"] == []
    assert (await get_course(client, course["id"])).json()["is_archived"] is True
    assert (await client.post(f"{course_url}/unarchive")).status_code == 403

    await sign_in(client, "teacher@example.com", "password-1")
    restored = await client.post(f"{course_url}/unarchive")
    assert restored.json()["is_archived"] is False
    assert [c["id"] for c in (await client.get("/api/courses")).json()["items"]] == [course["id"]]
