import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import autumn_course


def exam_body(group_id: object, **fields: object) -> dict[str, object]:
    return {
        "group_id": str(group_id),
        "exam_type": "exam",
        "day": "2027-01-12",
        "slot": 2,
        "room": "А-205",
        **fields,
    }


@pytest.mark.case(id="UC-T16-001")
async def test_teacher_assigns_exam(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    url = f"/api/courses/{course['id']}/exams"

    created = await client.post(url, json=exam_body(group.id))
    exam = created.json()
    changed = await client.put(
        f"{url}/{exam['id']}",
        json=exam_body(group.id, exam_type="graded_credit", day="2026-12-25", slot=4, room=" "),
    )
    listed = (await client.get(url)).json()["items"]
    deleted = await client.delete(f"{url}/{exam['id']}")

    assert created.status_code == 201, created.text
    assert (exam["exam_type"], exam["day"], exam["slot"], exam["room"]) == (
        "exam",
        "2027-01-12",
        2,
        "А-205",
    )
    assert (exam["starts_at"], exam["ends_at"]) == ("11:15:00", "12:45:00")
    assert exam["group"] == {"id": str(group.id), "name": "БВТ2601"}
    assert changed.status_code == 200, changed.text
    assert (changed.json()["exam_type"], changed.json()["slot"], changed.json()["room"]) == (
        "graded_credit",
        4,
        None,
    )
    assert [item["id"] for item in listed] == [exam["id"]]
    assert deleted.status_code == 204
    assert (await client.get(url)).json()["items"] == []


@pytest.mark.case(id="UC-T16-002")
async def test_exam_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    url = f"/api/courses/{course['id']}/exams"
    first = await client.post(url, json=exam_body(group.id))

    # Сессия идёт после конца пар, но до конца семестра (31 января).
    in_session = await client.post(url, json=exam_body(other_group.id, day="2027-01-31"))
    duplicate = await client.post(url, json=exam_body(group.id, day="2027-01-20"))
    before_semester = await client.put(
        f"{url}/{first.json()['id']}", json=exam_body(group.id, day="2026-08-31")
    )
    after_semester = await client.put(
        f"{url}/{first.json()['id']}", json=exam_body(group.id, day="2027-02-01")
    )
    bad_slot = await client.put(f"{url}/{first.json()['id']}", json=exam_body(group.id, slot=6))
    bad_type = await client.put(
        f"{url}/{first.json()['id']}", json=exam_body(group.id, exam_type="test")
    )
    foreign_group = await client.post(url, json=exam_body(other_group.id))
    missing = await client.delete(f"{url}/00000000-0000-7000-8000-000000000000")

    assert first.status_code == 201
    assert (foreign_group.status_code, error_code(foreign_group)) == (
        422,
        "exams.group_not_in_course",
    )
    assert (in_session.status_code, error_code(in_session)) == (422, "exams.group_not_in_course")
    assert (duplicate.status_code, error_code(duplicate)) == (409, "exams.already_exists")
    for rejected in (before_semester, after_semester):
        assert (rejected.status_code, error_code(rejected)) == (
            422,
            "exams.date_outside_semester",
        )
    assert (bad_slot.status_code, error_code(bad_slot)) == (422, "exams.slot_not_found")
    assert (bad_type.status_code, error_code(bad_type)) == (422, "request.invalid")
    assert (missing.status_code, error_code(missing)) == (404, "exams.not_found")

    await sign_in(client, "student@example.com", "password-1")
    student = await client.post(url, json=exam_body(group.id))
    assert (student.status_code, error_code(student)) == (403, "exams.course_forbidden")

    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.delete(f"{url}/{first.json()['id']}")
    assert (archived.status_code, error_code(archived)) == (409, "exams.course_archived")


@pytest.mark.case(id="UC-T16-003")
async def test_exam_for_second_group_and_visibility(client: AsyncClient, db: AsyncSession) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    await create_student(client, db, first, "CODE-1", "first@example.com")
    await create_student(client, db, second, "CODE-2", "second@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id, second.id], term="autumn", year=2026)
    url = f"/api/courses/{course['id']}/exams"
    await client.post(url, json=exam_body(first.id, exam_type="credit", day="2026-12-28"))
    await client.post(url, json=exam_body(second.id, day="2027-01-12"))

    teacher = (await client.get(url)).json()["items"]
    await sign_in(client, "second@example.com", "password-1")
    student = (await client.get(url)).json()["items"]
    moved = await client.post(url, json=exam_body(second.id))

    assert [(item["group"]["name"], item["exam_type"]) for item in teacher] == [
        ("БВТ2601", "credit"),
        ("БВТ2602", "exam"),
    ]
    assert [item["group"]["name"] for item in student] == ["БВТ2602"]
    assert moved.status_code == 403
