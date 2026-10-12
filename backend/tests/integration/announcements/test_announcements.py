from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.assignments import course_with_student
from tests.support.auth import error_code
from tests.support.courses import create_course, sign_in


@pytest.mark.case(id="UC-T6-001")
async def test_teacher_manages_announcements(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    other = await create_course(client, [course["groups"][0]["id"]], name="Другой курс")
    url = f"/api/courses/{course['id']}/announcements"

    created = await client.post(url, json={"text": " Пара переносится на **12:10** "})
    assert created.status_code == 201, created.text
    announcement = created.json()
    assert announcement["text"] == "Пара переносится на **12:10**"
    edited = await client.put(f"{url}/{announcement['id']}", json={"text": "Пара отменена"})
    foreign = await client.put(
        f"/api/courses/{other['id']}/announcements/{announcement['id']}", json={"text": "x"}
    )
    empty = await client.post(url, json={"text": "   "})

    assert edited.status_code == 200, edited.text
    assert edited.json()["text"] == "Пара отменена"
    assert datetime.fromisoformat(edited.json()["updated_at"]) > datetime.fromisoformat(
        announcement["updated_at"]
    )
    assert (foreign.status_code, error_code(foreign)) == (404, "announcements.not_found")
    assert (empty.status_code, error_code(empty)) == (422, "request.invalid")

    await sign_in(client, "student@example.com", "password-1")
    student = await client.post(url, json={"text": "Привет"})
    assert (student.status_code, error_code(student)) == (403, "announcements.course_forbidden")

    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=True))
    await db.commit()
    archived = await client.delete(f"{url}/{announcement['id']}")
    assert (archived.status_code, error_code(archived)) == (409, "announcements.course_archived")
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=False))
    await db.commit()

    deleted = await client.delete(f"{url}/{announcement['id']}")
    assert deleted.status_code == 204
    feed = (await client.get(f"/api/courses/{course['id']}/feed")).json()
    assert feed["items"] == []
