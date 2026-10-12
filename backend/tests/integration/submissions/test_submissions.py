from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course, Submission
from tests.support.assignments import (
    assignment_body,
    course_with_student,
    create_assignment,
    review,
    submissions_url,
    submit,
    upload,
)
from tests.support.auth import error_code
from tests.support.courses import sign_in
from tests.support.files import download, is_in_s3


def past() -> str:
    return (datetime.now(UTC) - timedelta(hours=1)).isoformat()


def future() -> str:
    return (datetime.now(UTC) + timedelta(days=1)).isoformat()


@pytest.mark.case(id="UC-S4-001")
async def test_student_submits_attempt(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    other = await create_assignment(client, course["id"], title="Другое")
    url = submissions_url(course["id"], assignment["id"])
    teacher = await client.post(url, json={"comment": "Я преподаватель"})
    await sign_in(client, "student@example.com", "password-1")

    created = await submit(client, course["id"], assignment["id"], "Сделал", b"main.py")
    empty = await client.post(url, json={"comment": "  ", "files": []})
    other_form = (
        await client.post(
            f"{submissions_url(course['id'], other['id'])}/uploads",
            json={"content_type": "text/plain", "file_size": 3},
        )
    ).json()
    foreign = await client.post(
        url, json={"files": [{"key": other_form["key"], "file_name": "a.txt"}]}
    )

    assert (teacher.status_code, error_code(teacher)) == (403, "submissions.student_only")
    assert created.status_code == 201, created.text
    attempt = created.json()
    assert (attempt["number"], attempt["comment"], attempt["is_late"], attempt["review"]) == (
        1,
        "Сделал",
        False,
        None,
    )
    assert (await download(attempt["files"][0]["download_url"])).content == b"main.py"
    assert (empty.status_code, error_code(empty)) == (422, "submissions.empty")
    assert (foreign.status_code, error_code(foreign)) == (422, "submissions.foreign_file_key")
    history = (await client.get(url)).json()["items"]
    assert [item["number"] for item in history] == [1]
    card = (await client.get(f"/api/courses/{course['id']}/assignments/{assignment['id']}")).json()
    assert (card["my_progress"]["status"], card["my_progress"]["attempts"]) == ("on_review", 1)


@pytest.mark.case(id="UC-S4-002")
async def test_deadlines_are_applied(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    soft = await create_assignment(client, course["id"], deadline_type="soft", deadline_at=past())
    hard = await create_assignment(client, course["id"], deadline_type="hard", deadline_at=past())
    await sign_in(client, "student@example.com", "password-1")

    late = await submit(client, course["id"], soft["id"])
    too_late = await submit(client, course["id"], hard["id"])
    upload_too_late = await client.post(
        f"{submissions_url(course['id'], hard['id'])}/uploads",
        json={"content_type": "text/plain", "file_size": 3},
    )

    assert late.status_code == 201, late.text
    assert late.json()["is_late"] is True
    assert (too_late.status_code, error_code(too_late)) == (409, "submissions.deadline_passed")
    assert (upload_too_late.status_code, error_code(upload_too_late)) == (
        409,
        "submissions.deadline_passed",
    )


@pytest.mark.case(id="UC-S4-003")
async def test_accepted_or_archived_blocks_submission(
    client: AsyncClient, db: AsyncSession
) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    other = await create_assignment(client, course["id"], title="Другое")
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], assignment["id"])).json()
    await sign_in(client, "teacher@example.com", "password-1")
    assert (
        await review(client, course["id"], assignment["id"], attempt["id"], "accepted", score=5)
    ).status_code == 201
    await sign_in(client, "student@example.com", "password-1")

    again = await submit(client, course["id"], assignment["id"])
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await submit(client, course["id"], other["id"])
    history = await client.get(submissions_url(course["id"], assignment["id"]))

    assert (again.status_code, error_code(again)) == (409, "submissions.already_accepted")
    assert (archived.status_code, error_code(archived)) == (409, "submissions.course_archived")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1


@pytest.mark.case(id="UC-S5-001")
async def test_hard_deadline_allows_resubmission_after_revision(
    client: AsyncClient, db: AsyncSession
) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(
        client, course["id"], deadline_type="hard", deadline_at=future()
    )
    card = f"/api/courses/{course['id']}/assignments/{assignment['id']}"
    await sign_in(client, "student@example.com", "password-1")
    first = (await submit(client, course["id"], assignment["id"], "v1")).json()
    # Первая попытка была за два часа до дедлайна, а дедлайн прошёл час назад.
    await db.execute(
        update(Submission)
        .where(Submission.id == first["id"])
        .values(created_at=datetime.now(UTC) - timedelta(hours=2))
    )
    await db.commit()
    await sign_in(client, "teacher@example.com", "password-1")
    moved = await client.put(card, json=assignment_body(deadline_type="hard", deadline_at=past()))
    assert moved.status_code == 200, moved.text
    await sign_in(client, "student@example.com", "password-1")

    while_on_review = await submit(client, course["id"], assignment["id"], "v2")
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], assignment["id"], first["id"], "revision")
    await sign_in(client, "student@example.com", "password-1")
    after_revision = await submit(client, course["id"], assignment["id"], "v2")

    assert (while_on_review.status_code, error_code(while_on_review)) == (
        409,
        "submissions.deadline_passed",
    )
    assert after_revision.status_code == 201, after_revision.text
    assert (after_revision.json()["number"], after_revision.json()["is_late"]) == (2, False)


@pytest.mark.case(id="UC-S5-002")
async def test_new_attempt_replaces_unreviewed_one(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    await sign_in(client, "student@example.com", "password-1")
    first = (await submit(client, course["id"], assignment["id"], "v1")).json()
    second = (await submit(client, course["id"], assignment["id"], "v2")).json()
    await sign_in(client, "teacher@example.com", "password-1")

    queue = (await client.get("/api/reviews/queue")).json()["items"]
    stale = await review(client, course["id"], assignment["id"], first["id"], "revision")

    assert [item["submission_id"] for item in queue] == [second["id"]]
    assert (stale.status_code, error_code(stale)) == (409, "reviews.not_latest")


@pytest.mark.case(id="UC-S6-001")
async def test_student_sees_result_and_current_grade(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    await sign_in(client, "student@example.com", "password-1")
    first = (await submit(client, course["id"], assignment["id"], "v1")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], assignment["id"], first["id"], "revision", score=4)
    await sign_in(client, "student@example.com", "password-1")
    second = (await submit(client, course["id"], assignment["id"], "v2")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], assignment["id"], second["id"], "revision")
    await sign_in(client, "student@example.com", "password-1")

    history = (await client.get(submissions_url(course["id"], assignment["id"]))).json()["items"]
    card = (await client.get(f"/api/courses/{course['id']}/assignments/{assignment['id']}")).json()

    assert [item["number"] for item in history] == [2, 1]
    assert history[1]["review"]["verdict"] == "revision"
    assert history[1]["review"]["grade"] == {"score": 4, "passed": None}
    assert history[1]["review"]["comment"] == "Комментарий"
    assert history[0]["review"]["grade"] is None
    # Текущая оценка — из последней проверенной попытки, где она выставлена.
    assert card["my_progress"]["status"] == "revision"
    assert card["my_progress"]["grade"] == {"score": 4, "passed": None}


@pytest.mark.case(id="UC-S4-004")
async def test_rejected_attempt_discards_uploaded_files(
    client: AsyncClient, db: AsyncSession
) -> None:
    course = await course_with_student(client, db)
    assignment = await create_assignment(client, course["id"])
    url = submissions_url(course["id"], assignment["id"])
    await sign_in(client, "student@example.com", "password-1")
    first = await upload(client, f"{url}/uploads", b"first", "a.pdf")
    second = await upload(client, f"{url}/uploads", b"second", "b.pdf")
    kept = await client.post(url, json={"files": [first]})
    assert kept.status_code == 201, kept.text
    for_accepted = await upload(client, f"{url}/uploads", b"for-accepted", "c.pdf")
    for_archive = await upload(client, f"{url}/uploads", b"for-archive", "d.pdf")

    duplicate = await client.post(url, json={"files": [first, second]})
    await sign_in(client, "teacher@example.com", "password-1")
    attempt_id = kept.json()["id"]
    accepted = await review(client, course["id"], assignment["id"], attempt_id, "accepted", score=5)
    await sign_in(client, "student@example.com", "password-1")
    after_accepted = await client.post(url, json={"files": [for_accepted]})
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=True))
    await db.commit()
    archived = await client.post(url, json={"files": [for_archive]})

    assert accepted.status_code == 201, accepted.text
    assert (duplicate.status_code, after_accepted.status_code, archived.status_code) == (
        409,
        409,
        409,
    )
    assert await is_in_s3(first["key"])
    assert not await is_in_s3(second["key"])
    assert not await is_in_s3(for_accepted["key"])
    assert not await is_in_s3(for_archive["key"])
