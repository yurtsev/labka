from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import AssignmentFile, Course, User
from src.core.s3.service import S3Storage
from tests.support.assignments import (
    assignment_body,
    course_with_student,
    create_assignment,
    review,
    submit,
    upload,
)
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.files import download, is_in_s3, s3_unavailable


def assignment_url(course: dict, assignment: dict | None = None) -> str:
    url = f"/api/courses/{course['id']}/assignments"
    return f"{url}/{assignment['id']}" if assignment else url


@pytest.mark.case(id="UC-T7-001")
async def test_teacher_creates_assignment(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    file = await upload(client, f"{url}/uploads", b"%PDF guide", "Указания.pdf")

    response = await client.post(
        url,
        json=assignment_body(deadline_type="hard", deadline_at="2030-10-12T23:59:00", files=[file]),
    )
    own_scale = await create_assignment(
        client, course["id"], title="Зачётная", scale={"type": "binary"}
    )

    assert response.status_code == 201, response.text
    assignment = response.json()
    assert (assignment["type"], assignment["title"], assignment["deadline_type"]) == (
        "lab",
        "Сортировки",
        "hard",
    )
    # Время без пояса — московское и отдаётся по МСК.
    assert assignment["deadline_at"] == "2030-10-12T23:59:00+03:00"
    assert (assignment["scale"], assignment["has_own_scale"]) == (
        {"type": "range", "min": 2, "max": 5},
        False,
    )
    assert (own_scale["scale"]["type"], own_scale["has_own_scale"]) == ("binary", True)
    assert [f["file_name"] for f in assignment["files"]] == ["Указания.pdf"]
    assert (await download(assignment["files"][0]["download_url"])).content == b"%PDF guide"
    assert assignment["summary"] == {"students": 1, "submitted": 0, "on_review": 0, "accepted": 0}
    assert (assignment["attempts_total"], assignment["my_progress"]) == (0, None)

    await sign_in(client, "student@example.com", "password-1")
    seen = (await client.get(assignment_url(course, assignment))).json()
    assert seen["my_progress"]["status"] == "not_submitted"
    assert (seen["summary"], seen["attempts_total"]) == (None, None)


@pytest.mark.case(id="UC-T7-002")
async def test_assignment_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    material_form = (
        await client.post(
            f"/api/courses/{course['id']}/materials/uploads",
            json={"content_type": "text/plain", "file_size": 3},
        )
    ).json()

    no_date = await client.post(url, json=assignment_body(deadline_type="soft"))
    extra_date = await client.post(
        url, json=assignment_body(deadline_at="2030-01-01T00:00:00+03:00")
    )
    bad_scale = await client.post(
        url, json=assignment_body(scale={"type": "range", "min": 5, "max": 2})
    )
    foreign = await client.post(
        url,
        json=assignment_body(files=[{"key": material_form["key"], "file_name": "a.txt"}]),
    )

    for response in (no_date, extra_date, bad_scale):
        assert (response.status_code, error_code(response)) == (422, "request.invalid")
    assert (foreign.status_code, error_code(foreign)) == (422, "assignments.foreign_file_key")

    await sign_in(client, "student@example.com", "password-1")
    student = await client.post(url, json=assignment_body())
    assert (student.status_code, error_code(student)) == (403, "assignments.course_forbidden")

    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.post(url, json=assignment_body())
    assert (archived.status_code, error_code(archived)) == (409, "assignments.course_archived")


@pytest.mark.case(id="UC-T8-001")
async def test_assignment_is_edited(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    first = await upload(client, f"{url}/uploads", b"old", "old.pdf")
    assignment = await create_assignment(client, course["id"], files=[first])
    card = assignment_url(course, assignment)

    rescaled = await client.put(card, json=assignment_body(scale={"type": "binary"}))
    assert rescaled.status_code == 200, rescaled.text
    assert rescaled.json()["scale"]["type"] == "binary"
    added = await client.post(
        f"{card}/files", json=await upload(client, f"{url}/uploads", b"new", "new.pdf")
    )
    assert added.status_code == 201, added.text
    removed = await client.delete(f"{card}/files/{assignment['files'][0]['id']}")
    assert removed.status_code == 204
    assert (await download(assignment["files"][0]["download_url"])).status_code == 404

    await sign_in(client, "student@example.com", "password-1")
    assert (await submit(client, course["id"], assignment["id"])).status_code == 201
    await sign_in(client, "teacher@example.com", "password-1")

    locked = await client.put(card, json=assignment_body(scale=None))
    edited = await client.put(
        card,
        json=assignment_body(
            title="Сортировки v2",
            scale={"type": "binary"},
            deadline_type="soft",
            deadline_at="2030-01-01T10:00:00+03:00",
        ),
    )
    assert (locked.status_code, error_code(locked)) == (409, "assignments.scale_locked")
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert (body["title"], body["deadline_type"]) == ("Сортировки v2", "soft")
    assert [f["file_name"] for f in body["files"]] == ["new.pdf"]
    assert datetime.fromisoformat(body["updated_at"]) > datetime.fromisoformat(
        assignment["updated_at"]
    )


@pytest.mark.case(id="UC-T9-001")
async def test_assignment_is_deleted_with_attempts(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    own = await upload(client, f"{url}/uploads", b"guide", "guide.pdf")
    assignment = await create_assignment(client, course["id"], files=[own])
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], assignment["id"], None, b"work")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    assert (await client.get(assignment_url(course, assignment))).json()["attempts_total"] == 1

    deleted = await client.delete(assignment_url(course, assignment))

    assert deleted.status_code == 204
    assert (await client.get(assignment_url(course, assignment))).status_code == 404
    assert (await download(assignment["files"][0]["download_url"])).status_code == 404
    assert (await download(attempt["files"][0]["download_url"])).status_code == 404


@pytest.mark.case(id="UC-T9-002")
async def test_assignment_survives_s3_failure(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    own = await upload(client, f"{url}/uploads", b"guide", "guide.pdf")
    assignment = await create_assignment(client, course["id"], files=[own])
    monkeypatch.setattr(S3Storage, "delete", s3_unavailable)
    monkeypatch.setattr(S3Storage, "delete_many", s3_unavailable)

    whole = await client.delete(assignment_url(course, assignment))
    one_file = await client.delete(
        f"{assignment_url(course, assignment)}/files/{assignment['files'][0]['id']}"
    )

    assert (whole.status_code, error_code(whole)) == (503, "s3.unavailable")
    assert (one_file.status_code, error_code(one_file)) == (503, "s3.unavailable")
    kept = (await client.get(assignment_url(course, assignment))).json()
    assert [f["id"] for f in kept["files"]] == [assignment["files"][0]["id"]]
    assert (await download(kept["files"][0]["download_url"])).content == b"guide"


@pytest.mark.case(id="UC-T10-001")
async def test_teacher_sees_students_by_assignment(client: AsyncClient, db: AsyncSession) -> None:
    course = await course_with_student(client, db)
    second_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, second_group, "CODE-2", "second@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    # Студент группы не из курса в таблицу не попадает.
    assignment = await create_assignment(
        client,
        course["id"],
        deadline_type="soft",
        deadline_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
    )
    await sign_in(client, "student@example.com", "password-1")
    first_try = (await submit(client, course["id"], assignment["id"], "v1")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], assignment["id"], first_try["id"], "revision", score=3)
    await sign_in(client, "student@example.com", "password-1")
    await submit(client, course["id"], assignment["id"], "v2")
    await sign_in(client, "teacher@example.com", "password-1")
    url = f"{assignment_url(course, assignment)}/students"

    rows = (await client.get(url)).json()["items"]
    on_review = (await client.get(url, params={"status": "on_review"})).json()["items"]
    not_submitted = (await client.get(url, params={"status": "not_submitted"})).json()["items"]

    [row] = rows
    assert (row["last_name"], row["group_name"]) == ("Иванов", "БВТ2601")
    progress = row["progress"]
    assert (progress["status"], progress["grade"], progress["attempts"]) == (
        "on_review",
        {"score": 3, "passed": None},
        2,
    )
    assert progress["last_is_late"] is True
    assert [r["student_id"] for r in on_review] == [row["student_id"]]
    assert not_submitted == []
    by_group = await client.get(url, params={"group_id": str(second_group.id)})
    assert by_group.json()["items"] == []

    await sign_in(client, "student@example.com", "password-1")
    student = await client.get(url)
    assert (student.status_code, error_code(student)) == (403, "assignments.teacher_only")


@pytest.mark.case(id="UC-T7-003")
async def test_rejected_assignment_discards_uploaded_files(
    client: AsyncClient, db: AsyncSession
) -> None:
    course = await course_with_student(client, db)
    url = assignment_url(course)
    created = await client.post(
        url, json=assignment_body(files=[await upload(client, f"{url}/uploads", b"kept", "a.pdf")])
    )
    assert created.status_code == 201, created.text
    attached = await db.scalar(select(AssignmentFile.file_key))
    assert attached is not None
    fresh = await upload(client, f"{url}/uploads", b"fresh", "b.pdf")
    invalid = await upload(client, f"{url}/uploads", b"invalid", "c.pdf")
    for_archive = await upload(client, f"{url}/uploads", b"for-archive", "d.pdf")

    duplicate = await client.post(
        url, json=assignment_body(files=[{"key": attached, "file_name": "a"}, fresh])
    )
    no_title = await client.post(url, json=assignment_body(title=" ", files=[invalid]))
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=True))
    await db.commit()
    archived = await client.post(url, json=assignment_body(files=[for_archive]))

    assert (duplicate.status_code, no_title.status_code, archived.status_code) == (409, 422, 409)
    assert await is_in_s3(attached)
    assert not await is_in_s3(fresh["key"])
    assert not await is_in_s3(for_archive["key"])
    assert await is_in_s3(invalid["key"])


@pytest.mark.case(id="UC-T10-002")
async def test_students_table_is_paged_and_filtered_in_db(
    client: AsyncClient, db: AsyncSession
) -> None:
    first_group = await create_group(db, name="БВТ2601", code="CODE-1")
    second_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first_group, second_group])
    student_ids = []
    for email, group, code in [
        ("s1@example.com", first_group, "CODE-1"),
        ("s2@example.com", first_group, "CODE-1"),
        ("s3@example.com", first_group, "CODE-1"),
        ("s4@example.com", second_group, "CODE-2"),
    ]:
        await create_student(client, db, group, code, email)
        student_ids.append((await client.get("/api/profile")).json()["id"])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first_group.id, second_group.id])
    assignment = await create_assignment(client, course["id"])
    attempts = {}
    for email in ("s1@example.com", "s2@example.com", "s3@example.com"):
        await sign_in(client, email, "password-1")
        attempts[email] = (await submit(client, course["id"], assignment["id"], "v1")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    accepted = await review(
        client,
        course["id"],
        assignment["id"],
        attempts["s1@example.com"]["id"],
        "accepted",
        score=5,
    )
    revision = await review(
        client,
        course["id"],
        assignment["id"],
        attempts["s2@example.com"]["id"],
        "revision",
        score=3,
    )
    assert (accepted.status_code, revision.status_code) == (201, 201)
    url = f"{assignment_url(course, assignment)}/students"

    first_page = (await client.get(url, params={"per_page": 2})).json()
    second_page = (await client.get(url, params={"per_page": 2, "page": 2})).json()
    beyond = (await client.get(url, params={"per_page": 2, "page": 3})).json()
    too_many = await client.get(url, params={"per_page": 101})

    assert (first_page["total"], first_page["pages"], first_page["page"]) == (4, 2, 1)
    assert [r["student_id"] for r in first_page["items"]] == student_ids[:2]
    assert [r["student_id"] for r in second_page["items"]] == student_ids[2:]
    assert [r["progress"]["status"] for r in first_page["items"] + second_page["items"]] == [
        "accepted",
        "revision",
        "on_review",
        "not_submitted",
    ]
    assert first_page["items"][1]["progress"]["grade"] == {"score": 3, "passed": None}
    assert (beyond["items"], beyond["total"]) == ([], 4)
    assert too_many.status_code == 422

    for status, expected in [
        ("accepted", student_ids[:1]),
        ("revision", student_ids[1:2]),
        ("on_review", student_ids[2:3]),
        ("not_submitted", student_ids[3:]),
    ]:
        filtered = (await client.get(url, params={"status": status})).json()
        assert [r["student_id"] for r in filtered["items"]] == expected, status
        assert filtered["total"] == 1
    by_group = (await client.get(url, params={"group_id": str(first_group.id)})).json()
    assert (by_group["total"], len(by_group["items"])) == (3, 3)
    mixed = (
        await client.get(url, params={"group_id": str(first_group.id), "status": "not_submitted"})
    ).json()
    assert (mixed["items"], mixed["total"]) == ([], 0)

    await db.execute(update(User).where(User.email == "s3@example.com").values(is_active=False))
    await db.commit()
    left = (await client.get(url)).json()
    assert left["total"] == 3
    card = (await client.get(assignment_url(course, assignment))).json()
    assert card["summary"] == {"students": 3, "submitted": 2, "on_review": 0, "accepted": 1}
    assert card["attempts_total"] == 3
