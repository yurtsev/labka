from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course
from tests.support.assignments import create_assignment, review, submit
from tests.support.auth import create_group
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import add_extra, add_rule, autumn_course

# Вторник, 13 октября 2026, 10:00 МСК: идёт первая пара.
TODAY = datetime(2026, 10, 13, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.api.home.service.now_moscow", lambda: TODAY)


async def soft(client: AsyncClient, course_id: str, title: str, deadline: str | None) -> dict:
    if deadline is None:
        return await create_assignment(client, course_id, title=title)
    return await create_assignment(
        client, course_id, title=title, deadline_type="soft", deadline_at=deadline
    )


@pytest.mark.case(id="UC-S1-001")
async def test_student_home(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    # Расписание: сегодня 9:30 (идёт) и 13:00, завтра 11:15, в среду допом ещё одно.
    await add_rule(client, course["id"], group, weekday=2, slot=1)
    await add_rule(
        client, course["id"], group, weekday=2, slot=3, room=None, lesson_type="practice"
    )
    await add_rule(client, course["id"], group, weekday=3, slot=2, repeat="weekly")
    await add_extra(client, course["id"], group, "2026-10-14", slot=5)
    first = await soft(client, course["id"], "Первое", "2026-10-14T18:00:00+03:00")
    returned = await soft(client, course["id"], "На доработке", "2026-10-15T18:00:00+03:00")
    third = await soft(client, course["id"], "Третье", "2026-10-16T18:00:00+03:00")
    await soft(client, course["id"], "Четвёртое", "2026-10-17T18:00:00+03:00")
    await soft(client, course["id"], "Пятое", "2026-10-18T18:00:00+03:00")
    accepted = await soft(client, course["id"], "Принято", "2026-10-14T08:00:00+03:00")
    await soft(client, course["id"], "Давно прошло", "2026-10-10T08:00:00+03:00")
    await soft(client, course["id"], "Без срока", None)
    await sign_in(client, "student@example.com", "password-1")
    returned_attempt = (await submit(client, course["id"], returned["id"], "v1")).json()
    accepted_attempt = (await submit(client, course["id"], accepted["id"], "v1")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], returned["id"], returned_attempt["id"], "revision", score=3)
    await review(client, course["id"], accepted["id"], accepted_attempt["id"], "accepted", score=5)
    await sign_in(client, "student@example.com", "password-1")

    home = (await client.get("/api/home")).json()

    nearest = home["nearest_deadline"]
    assert (nearest["assignment_id"], nearest["title"], nearest["status"]) == (
        first["id"],
        "Первое",
        "not_submitted",
    )
    assert nearest["deadline_at"].startswith("2026-10-14T18:00:00") and nearest[
        "deadline_at"
    ].endswith("+03:00")
    assert (nearest["deadline_type"], nearest["type"]) == ("soft", "lab")
    assert nearest["course"] == {"id": course["id"], "name": "Алгоритмы"}
    assert nearest["teacher"]["last_name"] == "Петров"
    # Работа, возвращённая на доработку, остаётся в списке; принятая, прошедшая и без срока — нет.
    assert [(item["title"], item["status"]) for item in home["upcoming_deadlines"]] == [
        ("На доработке", "revision"),
        ("Третье", "not_submitted"),
        ("Четвёртое", "not_submitted"),
    ]
    assert home["pending_reviews"] is None
    assert [
        (item["day"], item["starts_at"], item["lesson_type"]) for item in home["upcoming_lessons"]
    ] == [
        ("2026-10-13", "09:30:00", "lab"),
        ("2026-10-13", "13:00:00", "practice"),
        ("2026-10-14", "11:15:00", "lab"),
    ]
    assert home["upcoming_lessons"][1]["room"] is None
    assert home["upcoming_lessons"][0]["course"]["name"] == "Алгоритмы"
    assert home["upcoming_lessons"][0]["group"]["name"] == "БВТ2601"
    [card] = home["courses"]
    assert (card["id"], card["not_submitted"], card["pending_reviews"]) == (course["id"], 6, None)
    assert card["groups"] == [{"id": str(group.id), "name": "БВТ2601"}]
    assert (home["courses_total"], third["id"] is not None) == (1, True)


@pytest.mark.case(id="UC-S1-002")
async def test_student_home_when_nothing_to_do(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    only = await soft(client, course["id"], "Единственное", "2026-10-14T18:00:00+03:00")
    archived_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, archived_group, "CODE-2", "alone@example.com")
    alone = (await client.get("/api/home")).json()
    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], only["id"], "Готово")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], only["id"], attempt["id"], "accepted", score=5)
    await sign_in(client, "student@example.com", "password-1")

    done = (await client.get("/api/home")).json()
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = (await client.get("/api/home")).json()

    empty: dict[str, object] = {
        "nearest_deadline": None,
        "upcoming_deadlines": [],
        "pending_reviews": None,
        "upcoming_lessons": [],
        "courses": [],
        "courses_total": 0,
    }
    assert alone == empty
    assert done["nearest_deadline"] is None and done["upcoming_deadlines"] == []
    assert [(c["name"], c["not_submitted"]) for c in done["courses"]] == [("Алгоритмы", 0)]
    assert archived == empty
    assert group is not None


@pytest.mark.case(id="UC-T1-001")
async def test_teacher_home(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    second_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "other@example.com", "password-1", [second_group])
    await create_student(client, db, second_group, "CODE-2", "second@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    other_course = await create_course(
        client, [group.id], name="Базы данных", term="autumn", year=2026
    )
    await add_rule(client, course["id"], group, weekday=2, slot=1, room="305")
    await add_rule(client, other_course["id"], group, weekday=3, slot=2)
    await add_extra(client, course["id"], group, "2026-10-13", slot=4)
    work = await soft(client, course["id"], "Лаба", "2026-10-20T18:00:00+03:00")
    await soft(client, other_course["id"], "ДЗ", None)
    for email in ("student@example.com",):
        await sign_in(client, email, "password-1")
        await submit(client, course["id"], work["id"], "Готово")
    await sign_in(client, "second@example.com", "password-1")
    stranger = (await client.get("/api/home")).json()
    await sign_in(client, "teacher@example.com", "password-1")

    home = (await client.get("/api/home")).json()
    await sign_in(client, "other@example.com", "password-1")
    nobody = (await client.get("/api/home")).json()

    assert home["pending_reviews"] == 1
    assert home["nearest_deadline"] is None and home["upcoming_deadlines"] == []
    assert [
        (item["day"], item["starts_at"], item["room"], item["is_extra"])
        for item in home["upcoming_lessons"]
    ] == [
        ("2026-10-13", "09:30:00", "305", False),
        ("2026-10-13", "15:10:00", None, True),
        ("2026-10-14", "11:15:00", "Б-101", False),
    ]
    assert home["upcoming_lessons"][0]["group"]["name"] == "БВТ2601"
    assert {c["name"]: (c["pending_reviews"], c["not_submitted"]) for c in home["courses"]} == {
        "Алгоритмы": (1, None),
        "Базы данных": (0, None),
    }
    assert home["courses_total"] == 2
    assert (
        nobody["pending_reviews"] == 0
        and nobody["courses"] == []
        and nobody["upcoming_lessons"] == []
    )
    assert stranger["courses"] == []
