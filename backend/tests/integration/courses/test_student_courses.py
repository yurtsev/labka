import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, get_course, sign_in


@pytest.mark.case(id="UC-S2-001")
async def test_student_sees_only_own_group_courses(client: AsyncClient, db: AsyncSession) -> None:
    own = await create_group(db, name="БВТ2601", code="CODE-1")
    other = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [own, other])
    await create_student(client, db, own, "CODE-1", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    own_course = await create_course(client, [own.id], name="Алгоритмы")
    other_course = await create_course(client, [other.id], name="Базы данных")

    await sign_in(client, "student@example.com", "password-1")
    listing = await client.get("/api/courses")
    opened = await get_course(client, own_course["id"])
    foreign = await get_course(client, other_course["id"])

    assert [course["id"] for course in listing.json()["items"]] == [own_course["id"]]
    assert opened.status_code == 200
    assert opened.json()["teacher"]["last_name"] == "Петров"
    assert (foreign.status_code, error_code(foreign)) == (403, "courses.forbidden")
