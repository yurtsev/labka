import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.assignments import create_assignment, submit
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import add_extra, add_rule, autumn_course


def summary(calendar: dict) -> list[tuple[str, str, str | None]]:
    return [(item["day"], item["kind"], item["starts_at"]) for item in calendar["items"]]


@pytest.mark.case(id="UC-C8-001")
async def test_student_calendar_by_week(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    await add_rule(client, course["id"], group, weekday=2, slot=1, repeat="weekly")
    await add_rule(client, course["id"], group, weekday=4, slot=2, repeat="odd", room=None)
    await add_extra(client, course["id"], group, "2026-09-05")
    assignment = await create_assignment(
        client,
        course["id"],
        title="Лаба 1",
        deadline_type="soft",
        deadline_at="2026-09-03T18:00:00+03:00",
    )
    await create_assignment(client, course["id"], title="Без срока")
    await sign_in(client, "student@example.com", "password-1")
    await client.post(
        "/api/personal-tasks",
        json={"title": "Купить тетрадь", "due_date": "2026-09-01", "due_time": None},
    )
    await client.post(
        "/api/personal-tasks",
        json={"title": "Спортзал", "due_date": "2026-09-03", "due_time": "19:00:00"},
    )
    await client.post(
        "/api/personal-tasks",
        json={"title": "Через неделю", "due_date": "2026-09-08", "due_time": None},
    )

    week = (await client.get("/api/calendar", params={"view": "week", "date": "2026-09-02"})).json()
    after_submit_status = None
    await submit(client, course["id"], assignment["id"], "готово")
    refreshed = (await client.get("/api/calendar", params={"date": "2026-09-02"})).json()
    for item in refreshed["items"]:
        if item["kind"] == "deadline":
            after_submit_status = item["deadline"]["my_status"]

    assert week["period"] == {
        "view": "week",
        "starts_on": "2026-08-31",
        "ends_on": "2026-09-06",
        "prev": "2026-08-24",
        "next": "2026-09-07",
    }
    assert [(w["term"], w["number"], w["is_even"]) for w in week["weeks"]] == [("autumn", 1, False)]
    assert summary(week) == [
        ("2026-09-01", "task", None),
        ("2026-09-01", "lesson", "09:30:00"),
        ("2026-09-03", "lesson", "11:15:00"),
        ("2026-09-03", "deadline", "18:00:00"),
        ("2026-09-03", "task", "19:00:00"),
        ("2026-09-05", "lesson", "15:10:00"),
    ]
    lesson = week["items"][1]["lesson"]
    assert lesson["course"] == {"id": course["id"], "name": "Алгоритмы"}
    assert (lesson["group"]["name"], lesson["slot"], lesson["room"], lesson["is_extra"]) == (
        "БВТ2601",
        1,
        "Б-101",
        False,
    )
    assert week["items"][2]["lesson"]["room"] is None
    assert week["items"][5]["lesson"]["is_extra"] is True
    deadline = week["items"][3]
    assert deadline["deadline"]["title"] == "Лаба 1"
    assert deadline["deadline"]["my_status"] == "not_submitted"
    assert deadline["deadline"]["deadline_type"] == "soft"
    assert week["items"][4]["task"]["title"] == "Спортзал"
    assert after_submit_status == "on_review"


@pytest.mark.case(id="UC-C8-002")
async def test_calendar_views_and_parity(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    await add_rule(client, course["id"], group, weekday=2, slot=1, repeat="even")
    await sign_in(client, "student@example.com", "password-1")

    day = (await client.get("/api/calendar", params={"view": "day", "date": "2026-09-08"})).json()
    other_day = (
        await client.get("/api/calendar", params={"view": "day", "date": "2026-09-09"})
    ).json()
    month = (
        await client.get("/api/calendar", params={"view": "month", "date": "2026-09-15"})
    ).json()
    december = (
        await client.get("/api/calendar", params={"view": "month", "date": "2026-12-20"})
    ).json()
    default_view = await client.get("/api/calendar")
    bad_view = await client.get("/api/calendar", params={"view": "year"})

    assert day["period"]["prev"] == "2026-09-07"
    assert day["period"]["next"] == "2026-09-09"
    assert [item["kind"] for item in day["items"]] == ["lesson"]
    assert other_day["items"] == []
    # Чётная неделя: занятия 8, 22 сентября; нечётные недели занятий нет.
    assert [item["day"] for item in month["items"]] == ["2026-09-08", "2026-09-22"]
    assert (month["period"]["starts_on"], month["period"]["ends_on"]) == (
        "2026-08-31",
        "2026-10-04",
    )
    assert (month["period"]["prev"], month["period"]["next"]) == ("2026-08-01", "2026-10-01")
    assert [w["number"] for w in month["weeks"]] == [1, 2, 3, 4, 5]
    # Пары идут до 30 декабря включительно.
    assert december["items"][-1]["day"] == "2026-12-29"
    assert (december["period"]["starts_on"], december["period"]["ends_on"]) == (
        "2026-11-30",
        "2027-01-03",
    )
    assert default_view.status_code == 200
    assert default_view.json()["period"]["view"] == "week"
    assert (bad_view.status_code, error_code(bad_view)) == (422, "request.invalid")


@pytest.mark.case(id="UC-C8-003")
async def test_teacher_calendar_has_own_courses_only(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    await add_rule(client, course["id"], group, weekday=2, slot=3)
    await create_assignment(
        client, course["id"], deadline_type="soft", deadline_at="2026-09-02T12:00:00+03:00"
    )
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "other@example.com", "password-1", [other_group])
    await sign_in(client, "other@example.com", "password-1")
    other_course = await create_course(client, [other_group.id], term="autumn", year=2026)
    await add_rule(client, other_course["id"], other_group, weekday=2, slot=2)
    await sign_in(client, "teacher@example.com", "password-1")
    await client.post(
        f"/api/courses/{course['id']}/schedule/extras",
        json={
            "group_id": str(group.id),
            "lesson_type": "lab",
            "day": "2026-09-04",
            "slot": 5,
            "room": None,
        },
    )
    params = {"view": "week", "date": "2026-09-01"}

    own = (await client.get("/api/calendar", params=params)).json()
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=True))
    await db.commit()
    archived = (await client.get("/api/calendar", params=params)).json()
    await sign_in(client, "other@example.com", "password-1")
    other = (await client.get("/api/calendar", params=params)).json()

    assert summary(own) == [
        ("2026-09-01", "lesson", "13:00:00"),
        ("2026-09-02", "deadline", "12:00:00"),
        ("2026-09-04", "lesson", "16:55:00"),
    ]
    assert own["items"][0]["lesson"]["group"]["name"] == "БВТ2601"
    assert own["items"][1]["deadline"]["my_status"] is None
    assert archived["items"] == []
    assert summary(other) == [("2026-09-01", "lesson", "11:15:00")]

    await create_student(client, db, other_group, "CODE-2", "other-student@example.com")
    student = (await client.get("/api/calendar", params=params)).json()
    assert [item["lesson"]["course"]["id"] for item in student["items"]] == [other_course["id"]]


@pytest.mark.case(id="UC-C8-004")
async def test_calendar_shows_exams(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, other_group, "CODE-2", "other@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    created = await client.post(
        f"/api/courses/{course['id']}/exams",
        json={
            "group_id": str(group.id),
            "exam_type": "exam",
            "day": "2027-01-12",
            "slot": 3,
            "room": "А-205",
        },
    )
    assert created.status_code == 201, created.text
    params = {"view": "week", "date": "2027-01-13"}

    teacher = (await client.get("/api/calendar", params=params)).json()
    await sign_in(client, "student@example.com", "password-1")
    student = (await client.get("/api/calendar", params=params)).json()
    await sign_in(client, "other@example.com", "password-1")
    other = (await client.get("/api/calendar", params=params)).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = (await client.get("/api/calendar", params=params)).json()

    assert summary(teacher) == [("2027-01-12", "exam", "13:00:00")]
    exam = student["items"][0]["exam"]
    assert (exam["exam_type"], exam["slot"], exam["room"], exam["group"]["name"]) == (
        "exam",
        3,
        "А-205",
        "БВТ2601",
    )
    assert exam["course"] == {"id": course["id"], "name": "Алгоритмы"}
    assert student["items"][0]["lesson"] is None
    assert other["items"] == []
    assert archived["items"] == []
