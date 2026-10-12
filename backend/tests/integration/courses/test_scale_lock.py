import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.assignments import course_with_student, create_assignment, submit
from tests.support.auth import error_code
from tests.support.courses import course_body, sign_in


@pytest.mark.case(id="UC-T3-002")
async def test_course_scale_locked_by_attempts(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    inherits = await create_assignment(client, course["id"])
    own = await create_assignment(client, course["id"], title="Своя", scale={"type": "binary"})
    url = f"/api/courses/{course['id']}"
    binary = course_body([], scale={"type": "binary"})
    del binary["group_ids"]

    await sign_in(client, "student@example.com", "password-1")
    await submit(client, course["id"], own["id"])
    await sign_in(client, "teacher@example.com", "password-1")
    free = await client.put(url, json=binary)
    assert free.status_code == 200, free.text

    await sign_in(client, "student@example.com", "password-1")
    await submit(client, course["id"], inherits["id"])
    await sign_in(client, "teacher@example.com", "password-1")
    back = course_body([], scale={"type": "range", "min": 2, "max": 5})
    del back["group_ids"]
    locked = await client.put(url, json=back)
    renamed = await client.put(url, json={**binary, "name": "Алгоритмы 2"})

    assert (locked.status_code, error_code(locked)) == (409, "courses.scale_locked")
    assert renamed.status_code == 200, renamed.text
