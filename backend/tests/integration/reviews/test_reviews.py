from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.assignments import (
    course_with_student,
    create_assignment,
    review,
    submissions_url,
    submit,
)
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_teacher, sign_in


@pytest.mark.case(id="UC-T11-001")
async def test_teacher_reviews_attempt(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    ranged = await create_assignment(client, course["id"])
    binary = await create_assignment(client, course["id"], title="Зачёт", scale={"type": "binary"})
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], ranged["id"], "Готово", b"code")).json()
    binary_attempt = (await submit(client, course["id"], binary["id"])).json()
    await sign_in(client, "teacher@example.com", "password-1")
    args = (client, course["id"], ranged["id"], attempt["id"])

    no_grade = await review(*args, "accepted")
    out_of_range = await review(*args, "accepted", score=6)
    passed_on_range = await review(*args, "accepted", passed=True)
    score_on_binary = await review(
        client, course["id"], binary["id"], binary_attempt["id"], "accepted", score=5
    )
    accepted = await review(*args, "accepted", score=5)
    twice = await review(*args, "revision")
    passed = await review(
        client, course["id"], binary["id"], binary_attempt["id"], "accepted", passed=True
    )

    assert (no_grade.status_code, error_code(no_grade)) == (422, "reviews.grade_required")
    for response in (out_of_range, passed_on_range, score_on_binary):
        assert (response.status_code, error_code(response)) == (422, "reviews.grade_out_of_scale")
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["review"]["verdict"] == "accepted"
    assert accepted.json()["review"]["grade"] == {"score": 5, "passed": None}
    assert (twice.status_code, error_code(twice)) == (409, "reviews.already_reviewed")
    assert passed.json()["review"]["grade"] == {"score": None, "passed": True}

    student_id = (
        await client.get(f"/api/courses/{course['id']}/assignments/{ranged['id']}/students")
    ).json()["items"][0]["student_id"]
    screen = await client.get(
        f"/api/courses/{course['id']}/assignments/{ranged['id']}/students/{student_id}/submissions"
    )
    assert screen.status_code == 200, screen.text
    body = screen.json()
    assert body["scale"] == {"type": "range", "min": 2, "max": 5}
    assert [item["number"] for item in body["attempts"]] == [1]
    assert body["attempts"][0]["files"][0]["file_name"] == "1.pdf"

    await sign_in(client, "student@example.com", "password-1")
    by_student = await review(*args, "accepted", score=5)
    assert (by_student.status_code, error_code(by_student)) == (403, "reviews.course_forbidden")
    card = (await client.get(f"/api/courses/{course['id']}/assignments/{ranged['id']}")).json()
    assert card["my_progress"]["status"] == "accepted"


@pytest.mark.case(id="UC-T12-001")
async def test_teacher_corrects_grade(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], assignment["id"])).json()
    await sign_in(client, "teacher@example.com", "password-1")
    url = f"{submissions_url(course['id'], assignment['id'])}/{attempt['id']}/review"

    not_reviewed = await client.put(url, json={"grade": {"score": 4}})
    first = (
        await review(client, course["id"], assignment["id"], attempt["id"], "accepted", score=4)
    ).json()
    corrected = await client.put(url, json={"grade": {"score": 5}, "comment": "Пересмотрел"})
    removed_grade = await client.put(url, json={"grade": {}})

    assert (not_reviewed.status_code, error_code(not_reviewed)) == (409, "reviews.not_reviewed")
    assert corrected.status_code == 200, corrected.text
    review_body = corrected.json()["review"]
    assert (review_body["verdict"], review_body["grade"], review_body["comment"]) == (
        "accepted",
        {"score": 5, "passed": None},
        "Пересмотрел",
    )
    assert datetime.fromisoformat(review_body["updated_at"]) > datetime.fromisoformat(
        first["review"]["updated_at"]
    )
    assert (removed_grade.status_code, error_code(removed_grade)) == (
        422,
        "reviews.grade_required",
    )

    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.put(url, json={"grade": {"score": 3}})
    assert (archived.status_code, error_code(archived)) == (409, "reviews.course_archived")


@pytest.mark.case(id="UC-T13-001")
async def test_review_queue(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    other_course = await create_course(client, [course["groups"][0]["id"]], name="Сети")
    first = await create_assignment(client, course["id"], title="Первое")
    second = await create_assignment(client, other_course["id"], title="Второе")
    reviewed = await create_assignment(client, course["id"], title="Проверенное")
    stranger_group = await create_group(db, name="БВТ2609", code="CODE-9")
    await create_teacher(db, "stranger@example.com", "password-1", [stranger_group])
    await sign_in(client, "student@example.com", "password-1")
    first_attempt = (await submit(client, course["id"], first["id"])).json()
    second_attempt = (await submit(client, other_course["id"], second["id"])).json()
    done = (await submit(client, course["id"], reviewed["id"])).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], reviewed["id"], done["id"], "revision")

    queue = (await client.get("/api/reviews/queue")).json()
    by_course = (
        await client.get("/api/reviews/queue", params={"course_id": other_course["id"]})
    ).json()
    by_assignment = (
        await client.get("/api/reviews/queue", params={"assignment_id": first["id"]})
    ).json()

    assert [item["submission_id"] for item in queue["items"]] == [
        first_attempt["id"],
        second_attempt["id"],
    ]
    item = queue["items"][0]
    assert (item["student"]["last_name"], item["group"]["name"], item["course"]["name"]) == (
        "Иванов",
        "БВТ2601",
        "Алгоритмы",
    )
    assert (item["assignment"]["title"], item["number"], item["is_late"]) == ("Первое", 1, False)
    assert item["in_course"] is True
    assert [i["submission_id"] for i in by_course["items"]] == [second_attempt["id"]]
    assert [i["submission_id"] for i in by_assignment["items"]] == [first_attempt["id"]]

    await client.post(f"/api/courses/{other_course['id']}/archive")
    tiles = {
        c["id"]: c["pending_reviews"] for c in (await client.get("/api/courses")).json()["items"]
    }
    assert tiles[course["id"]] == 1
    after_archive = (await client.get("/api/reviews/queue")).json()["items"]
    assert [i["submission_id"] for i in after_archive] == [first_attempt["id"]]

    removed = await client.delete(f"/api/courses/{course['id']}/groups/{course['groups'][0]['id']}")
    assert removed.status_code == 200, removed.text
    after_removal = (await client.get("/api/reviews/queue")).json()["items"]
    assert [(i["submission_id"], i["in_course"]) for i in after_removal] == [
        (first_attempt["id"], False)
    ]
    home = (await client.get("/api/home")).json()
    assert home["pending_reviews"] == 1

    await sign_in(client, "stranger@example.com", "password-1")
    assert (await client.get("/api/reviews/queue")).json()["items"] == []
    await sign_in(client, "student@example.com", "password-1")
    student = await client.get("/api/reviews/queue")
    assert (student.status_code, error_code(student)) == (403, "reviews.teacher_only")
    student_tiles = (await client.get("/api/courses")).json()["items"]
    assert all(tile["pending_reviews"] is None for tile in student_tiles)
