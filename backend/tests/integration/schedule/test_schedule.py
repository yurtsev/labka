import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import add_extra, add_rule, autumn_course, rule_body


@pytest.mark.case(id="UC-T14-001")
async def test_teacher_manages_schedule_rules(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    url = f"/api/courses/{course['id']}/schedule"

    slots = (await client.get("/api/schedule/slots")).json()["items"]
    created = await add_rule(client, course["id"], group, weekday=2, slot=1, repeat="odd")
    changed = await client.put(
        f"{url}/rules/{created['id']}",
        json=rule_body(group, weekday=4, slot=5, repeat="even", lesson_type="practice", room=" "),
    )
    schedule = (await client.get(url)).json()
    deleted = await client.delete(f"{url}/rules/{created['id']}")
    after = (await client.get(url)).json()

    assert [(s["number"], s["starts_at"], s["ends_at"]) for s in slots] == [
        (1, "09:30:00", "11:00:00"),
        (2, "11:15:00", "12:45:00"),
        (3, "13:00:00", "14:30:00"),
        (4, "15:10:00", "16:40:00"),
        (5, "16:55:00", "18:25:00"),
    ]
    assert (created["slot"], created["starts_at"], created["ends_at"]) == (
        1,
        "09:30:00",
        "11:00:00",
    )
    assert (created["group"], created["room"]) == (
        {"id": str(group.id), "name": "БВТ2601"},
        "Б-101",
    )
    assert changed.status_code == 200, changed.text
    rule = changed.json()
    assert (rule["weekday"], rule["slot"], rule["repeat"], rule["lesson_type"], rule["room"]) == (
        4,
        5,
        "even",
        "practice",
        None,
    )
    assert (rule["starts_at"], rule["ends_at"]) == ("16:55:00", "18:25:00")
    assert schedule["semester"]["starts_on"] == "2026-09-01"
    assert [item["id"] for item in schedule["rules"]] == [created["id"]]
    assert deleted.status_code == 204
    assert (after["rules"], after["extras"]) == ([], [])


@pytest.mark.case(id="UC-T14-002")
async def test_schedule_rule_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    url = f"/api/courses/{course['id']}/schedule/rules"

    bad_slot = await client.post(url, json=rule_body(group, slot=6))
    outside_grid = await client.post(url, json=rule_body(group, slot=0))
    bad_weekday = await client.post(url, json=rule_body(group, weekday=8))
    foreign_group = await client.post(url, json=rule_body(other_group))
    missing = await client.put(f"{url}/00000000-0000-7000-8000-000000000000", json=rule_body(group))

    assert (bad_slot.status_code, error_code(bad_slot)) == (422, "schedule.slot_not_found")
    assert (outside_grid.status_code, error_code(outside_grid)) == (422, "request.invalid")
    assert (bad_weekday.status_code, error_code(bad_weekday)) == (422, "request.invalid")
    assert (foreign_group.status_code, error_code(foreign_group)) == (
        422,
        "schedule.group_not_in_course",
    )
    assert (missing.status_code, error_code(missing)) == (404, "schedule.rule_not_found")

    await sign_in(client, "student@example.com", "password-1")
    student = await client.post(url, json=rule_body(group))
    assert (student.status_code, error_code(student)) == (403, "schedule.course_forbidden")

    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.post(url, json=rule_body(group))
    assert (archived.status_code, error_code(archived)) == (409, "schedule.course_archived")


@pytest.mark.case(id="UC-T14-003")
async def test_extra_lessons_stay_inside_classes(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    url = f"/api/courses/{course['id']}/schedule/extras"

    first_day = await add_extra(client, course["id"], group, "2026-09-01")
    last_day = await add_extra(client, course["id"], group, "2026-12-30")
    before = await add_extra(client, course["id"], group, "2026-08-31")
    session_period = await add_extra(client, course["id"], group, "2026-12-31")
    bad_slot = await add_extra(client, course["id"], group, "2026-10-01", slot=9)
    moved = await client.put(
        f"{url}/{first_day.json()['id']}",
        json={
            "group_id": str(group.id),
            "lesson_type": "lab",
            "day": "2026-10-05",
            "slot": 2,
            "room": "А-1",
        },
    )
    moved_out = await client.put(
        f"{url}/{first_day.json()['id']}",
        json={
            "group_id": str(group.id),
            "lesson_type": "lab",
            "day": "2027-01-15",
            "slot": 2,
            "room": None,
        },
    )
    deleted = await client.delete(f"{url}/{last_day.json()['id']}")

    assert (first_day.status_code, last_day.status_code) == (201, 201)
    assert first_day.json()["starts_at"] == "15:10:00"
    for rejected in (before, session_period, moved_out):
        assert (rejected.status_code, error_code(rejected)) == (
            422,
            "schedule.date_outside_classes",
        )
    assert (bad_slot.status_code, error_code(bad_slot)) == (422, "schedule.slot_not_found")
    assert moved.status_code == 200, moved.text
    assert (moved.json()["day"], moved.json()["slot"], moved.json()["room"]) == (
        "2026-10-05",
        2,
        "А-1",
    )
    assert deleted.status_code == 204
    schedule = (await client.get(f"/api/courses/{course['id']}/schedule")).json()
    assert [item["day"] for item in schedule["extras"]] == ["2026-10-05"]
    gone = await client.delete(f"{url}/{last_day.json()['id']}")
    assert (gone.status_code, error_code(gone)) == (404, "schedule.extra_lesson_not_found")


@pytest.mark.case(id="UC-T14-004")
async def test_student_sees_only_own_group_schedule(client: AsyncClient, db: AsyncSession) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    await create_student(client, db, first, "CODE-1", "first@example.com")
    await create_student(client, db, second, "CODE-2", "second@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id, second.id], term="autumn", year=2026)
    await add_rule(client, course["id"], first, slot=1)
    await add_rule(client, course["id"], second, slot=2)
    await add_extra(client, course["id"], second, "2026-10-01")
    url = f"/api/courses/{course['id']}/schedule"

    teacher = (await client.get(url)).json()
    await sign_in(client, "second@example.com", "password-1")
    student = (await client.get(url)).json()

    assert sorted(item["group"]["name"] for item in teacher["rules"]) == ["БВТ2601", "БВТ2602"]
    assert [item["group"]["name"] for item in student["rules"]] == ["БВТ2602"]
    assert [item["group"]["name"] for item in student["extras"]] == ["БВТ2602"]

    stranger_group = await create_group(db, name="БВТ2603", code="CODE-3")
    await create_student(client, db, stranger_group, "CODE-3", "stranger@example.com")
    stranger = await client.get(url)
    assert (stranger.status_code, error_code(stranger)) == (403, "schedule.course_forbidden")
