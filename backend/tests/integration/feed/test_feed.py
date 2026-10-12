import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.assignments import course_with_student, create_assignment, review, submit
from tests.support.auth import create_group, error_code
from tests.support.courses import create_student, sign_in


@pytest.mark.case(id="UC-S2-002")
async def test_course_feed(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    url = f"/api/courses/{course['id']}/feed"
    lab = await create_assignment(client, course["id"], title="Лаба 1")
    announcement = (
        await client.post(
            f"/api/courses/{course['id']}/announcements", json={"text": "Пара переносится"}
        )
    ).json()
    homework = await create_assignment(client, course["id"], type="hw", title="ДЗ 1")
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], lab["id"])).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], lab["id"], attempt["id"], "revision", score=3)

    teacher_feed = (await client.get(url)).json()
    labs_only = (await client.get(url, params={"type": "lab"})).json()
    first_page = (await client.get(url, params={"per_page": 2})).json()

    assert [e["kind"] for e in teacher_feed["items"]] == [
        "assignment",
        "announcement",
        "assignment",
    ]
    assert [
        teacher_feed["items"][0]["assignment"]["id"],
        teacher_feed["items"][2]["assignment"]["id"],
    ] == [homework["id"], lab["id"]]
    assert teacher_feed["items"][1]["announcement"]["id"] == announcement["id"]
    assert teacher_feed["items"][2]["assignment"]["summary"] == {
        "students": 1,
        "submitted": 1,
        "on_review": 0,
        "accepted": 0,
    }
    assert teacher_feed["items"][2]["assignment"]["my_progress"] is None
    assert [e["assignment"]["id"] for e in labs_only["items"]] == [lab["id"]]
    assert (first_page["total"], first_page["pages"], len(first_page["items"])) == (3, 2, 2)

    await sign_in(client, "student@example.com", "password-1")
    student_feed = (await client.get(url)).json()["items"]
    lab_entry = student_feed[2]["assignment"]
    assert lab_entry["summary"] is None
    assert (lab_entry["my_progress"]["status"], lab_entry["my_progress"]["grade"]) == (
        "revision",
        {"score": 3, "passed": None},
    )
    assert student_feed[0]["assignment"]["my_progress"]["status"] == "not_submitted"

    outsider_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, outsider_group, "CODE-2", "outsider@example.com")
    outsider = await client.get(url)
    assert (outsider.status_code, error_code(outsider)) == (403, "feed.course_forbidden")
