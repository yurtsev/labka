from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course, Notification, User
from tests.support.assignments import create_assignment, review, submissions_url, submit
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import add_rule, assign_exam, autumn_course, rule_body


async def notifications(client: AsyncClient, unread: bool = False) -> list[dict]:
    response = await client.get("/api/notifications", params={"per_page": 100, "unread": unread})
    assert response.status_code == 200, response.text
    items: list[dict] = response.json()["items"]
    return items


def titles(items: list[dict]) -> list[str]:
    return [item["title"] for item in items]


@pytest.mark.case(id="UC-C7-001")
async def test_user_reads_notifications(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    for title in ("Первое", "Второе", "Третье"):
        await client.post(f"/api/courses/{course['id']}/announcements", json={"text": title})
        await client.post(
            f"/api/courses/{course['id']}/materials", json={"title": title, "files": []}
        )
    await sign_in(client, "student@example.com", "password-1")

    page_one = (await client.get("/api/notifications", params={"per_page": 3})).json()
    page_two = (await client.get("/api/notifications", params={"per_page": 3, "page": 3})).json()
    count = (await client.get("/api/notifications/unread-count")).json()
    newest = page_one["items"][0]
    read = await client.post(f"/api/notifications/{newest['id']}/read")
    read_again = await client.post(f"/api/notifications/{newest['id']}/read")
    unread = await notifications(client, unread=True)
    after_one = (await client.get("/api/notifications/unread-count")).json()
    everything = await client.post("/api/notifications/read-all")
    after_all = (await client.get("/api/notifications/unread-count")).json()
    nothing_left = await client.post("/api/notifications/read-all")

    assert (page_one["total"], page_one["pages"], len(page_one["items"])) == (7, 3, 3)
    assert len(page_two["items"]) == 1
    assert titles(page_one["items"]) == ["Новый материал", "Новое объявление", "Новый материал"]
    assert count == {"unread_count": 7}
    assert newest["course"] == {"id": course["id"], "name": "Алгоритмы"}
    assert newest["target"]["section"] == "materials"
    assert newest["target"]["course_id"] == course["id"]
    assert newest["is_read"] is False
    assert read.status_code == 200 and read.json()["is_read"] is True
    assert read_again.status_code == 200
    assert len(unread) == 6 and newest["id"] not in [item["id"] for item in unread]
    assert after_one == {"unread_count": 6}
    assert everything.json() == {"marked": 6, "unread_count": 0}
    assert after_all == {"unread_count": 0}
    assert nothing_left.json() == {"marked": 0, "unread_count": 0}
    assert all(item["is_read"] for item in await notifications(client))


@pytest.mark.case(id="UC-C7-002")
async def test_notifications_are_private(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    await create_student(client, db, group, "CODE-1", "second@example.com")
    await sign_in(client, "student@example.com", "password-1")
    own = (await notifications(client))[0]
    await sign_in(client, "second@example.com", "password-1")

    foreign = await client.post(f"/api/notifications/{own['id']}/read")
    missing = await client.post("/api/notifications/00000000-0000-7000-8000-000000000000/read")
    bad_page = await client.get("/api/notifications", params={"per_page": 101})
    client.cookies.clear()
    anonymous = await client.get("/api/notifications")

    for response in (foreign, missing):
        assert (response.status_code, error_code(response)) == (404, "notifications.not_found")
    assert bad_page.status_code == 422
    assert anonymous.status_code == 401
    await sign_in(client, "student@example.com", "password-1")
    assert (await client.get("/api/notifications/unread-count")).json() == {"unread_count": 1}


@pytest.mark.case(id="UC-C6-001")
async def test_students_are_notified_about_course_events(
    client: AsyncClient, db: AsyncSession
) -> None:
    course, group = await autumn_course(client, db)
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "other@example.com", "password-1", [other_group])
    await create_student(client, db, other_group, "CODE-2", "outsider@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    url = f"/api/courses/{course['id']}"

    assignment = await create_assignment(client, course["id"], title="Лаба 1")
    for title in ("Лаба 1.1", "Лаба 1.2"):
        edited = await client.put(
            f"{url}/assignments/{assignment['id']}",
            json={
                "type": "lab",
                "title": title,
                "description": None,
                "deadline_type": "none",
                "deadline_at": None,
                "scale": None,
                "grading_note": None,
            },
        )
        assert edited.status_code == 200, edited.text
    await client.post(f"{url}/announcements", json={"text": "Привет"})
    await client.post(f"{url}/materials", json={"title": "Учебник", "files": []})
    await add_rule(client, course["id"], group, weekday=2, slot=1)
    await add_rule(client, course["id"], group, weekday=3, slot=2)
    exam = await assign_exam(client, course["id"], group, "exam", "2027-01-12", 2)
    await client.put(
        f"{url}/exams/{exam['id']}",
        json={
            "group_id": str(group.id),
            "exam_type": "exam",
            "day": "2027-01-14",
            "slot": 3,
            "room": None,
        },
    )

    await sign_in(client, "student@example.com", "password-1")
    attempt = (await submit(client, course["id"], assignment["id"], "Готово")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await review(client, course["id"], assignment["id"], attempt["id"], "accepted", score=4)
    await client.put(
        f"{submissions_url(course['id'], assignment['id'])}/{attempt['id']}/review",
        json={"grade": {"score": 5}},
    )
    await sign_in(client, "student@example.com", "password-1")
    student_id = (await client.get("/api/profile")).json()["id"]
    await sign_in(client, "teacher@example.com", "password-1")
    await client.put(f"{url}/final-grades/{student_id}", json={"grade": 5})

    await sign_in(client, "student@example.com", "password-1")
    student = await notifications(client)
    await sign_in(client, "outsider@example.com", "password-1")
    outsider = await notifications(client)
    await sign_in(client, "teacher@example.com", "password-1")
    teacher = await notifications(client)

    # Новые первыми; серии правок (задание, расписание, экзамен, оценка) не плодят дубли.
    assert titles(student) == [
        "Итоговый результат выставлен",
        "Оценка исправлена",
        "Работа принята",
        "Экзамен изменён",
        "Назначен экзамен",
        "Расписание изменено",
        "Новый материал",
        "Новое объявление",
        "Задание изменено",
        "Новое задание",
        "Вас добавили в курс",
    ]
    by_type = {item["type"]: item for item in student}
    assert [item["type"] for item in student].count("assignment_updated") == 1
    assert [item["type"] for item in student].count("schedule_changed") == 1
    assert {
        "course_added",
        "assignment_created",
        "assignment_updated",
        "announcement_created",
        "material_added",
        "schedule_changed",
        "exam_assigned",
        "submission_reviewed",
        "grade_changed",
        "final_result_set",
    } <= set(by_type)
    # Повторная правка обновила данные существующего уведомления.
    assert by_type["assignment_updated"]["text"] == "«Лаба 1.2» в курсе «Алгоритмы»"
    assert by_type["assignment_created"]["target"] == {
        "section": "assignment",
        "course_id": course["id"],
        "assignment_id": assignment["id"],
        "submission_id": None,
        "student_id": None,
        "day": None,
    }
    assert by_type["exam_assigned"]["text"] == "«Алгоритмы»: 12 января в 11:15"
    assert by_type["exam_assigned"]["target"]["day"] == "2027-01-12"
    assert by_type["final_result_set"]["text"] == "«Алгоритмы»: 5 (отлично)"
    assert by_type["schedule_changed"]["target"]["section"] == "schedule"
    assert outsider == []
    assert [item["type"] for item in teacher] == ["submission_created"]
    created = teacher[0]
    assert created["text"].startswith("Иванов Иван") and "попытка №1" in created["text"]
    assert created["target"]["student_id"] == student_id
    assert created["target"]["submission_id"] == attempt["id"]
    assert created["target"]["assignment_id"] == assignment["id"]


@pytest.mark.case(id="UC-C6-002")
async def test_removed_exam_and_group_move_notify_both_groups(
    client: AsyncClient, db: AsyncSession
) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    await create_student(client, db, first, "CODE-1", "first@example.com")
    await create_student(client, db, second, "CODE-2", "second@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id, second.id], term="autumn", year=2026)
    rule = await add_rule(client, course["id"], first, slot=1)
    exam = await assign_exam(client, course["id"], first, "credit", "2026-12-28", 1)

    await client.put(
        f"/api/courses/{course['id']}/schedule/rules/{rule['id']}",
        json=rule_body(second, slot=1),
    )
    await client.delete(f"/api/courses/{course['id']}/exams/{exam['id']}")

    await sign_in(client, "first@example.com", "password-1")
    first_items = await notifications(client)
    await sign_in(client, "second@example.com", "password-1")
    second_items = await notifications(client)

    assert titles(first_items)[:2] == ["Зачёт отменён", "Расписание изменено"]
    assert [item["type"] for item in first_items].count("schedule_changed") == 1
    assert "Расписание изменено" in titles(second_items)
    assert "Зачёт отменён" not in titles(second_items)


@pytest.mark.case(id="UC-C6-003")
async def test_archived_courses_and_inactive_students_are_not_notified(
    client: AsyncClient, db: AsyncSession
) -> None:
    course, group = await autumn_course(client, db)
    await create_student(client, db, group, "CODE-1", "inactive@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    await db.execute(
        update(User).where(User.email == "inactive@example.com").values(is_active=False)
    )
    await db.commit()

    await client.post(f"/api/courses/{course['id']}/announcements", json={"text": "Привет"})

    await sign_in(client, "student@example.com", "password-1")
    active = await notifications(client)
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    await sign_in(client, "teacher@example.com", "password-1")
    archived = await client.post(f"/api/courses/{course['id']}/announcements", json={"text": "Ещё"})
    await sign_in(client, "student@example.com", "password-1")
    after_archive = await notifications(client)

    assert "Новое объявление" in titles(active)
    assert archived.status_code == 409
    assert len(after_archive) == len(active)
    inactive = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .join(User, User.id == Notification.user_id)
        .where(User.email == "inactive@example.com", Notification.type == "announcement_created")
    )
    assert inactive == 0


@pytest.mark.case(id="UC-SYS1-001")
async def test_deadline_reminders(client: AsyncClient, db: AsyncSession) -> None:
    from src.core.scheduler.service import SchedulerService
    from src.main import container

    course, group = await autumn_course(client, db)
    await create_student(client, db, group, "CODE-1", "submitted@example.com")
    await create_student(client, db, group, "CODE-1", "late@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    soon = (datetime.now(UTC) + timedelta(hours=5)).isoformat()
    far = (datetime.now(UTC) + timedelta(hours=40)).isoformat()
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    due = await create_assignment(
        client, course["id"], title="Скоро", deadline_type="hard", deadline_at=soon
    )
    await create_assignment(
        client, course["id"], title="Далеко", deadline_type="soft", deadline_at=far
    )
    await create_assignment(
        client, course["id"], title="Прошло", deadline_type="soft", deadline_at=past
    )
    await create_assignment(client, course["id"], title="Без срока")
    await sign_in(client, "submitted@example.com", "password-1")
    await submit(client, course["id"], due["id"], "Сдал")
    scheduler = await container.get(SchedulerService)

    first_run = await scheduler.remind_deadlines()
    second_run = await scheduler.remind_deadlines()

    async def reminders(email: str) -> list[dict]:
        await sign_in(client, email, "password-1")
        return [item for item in await notifications(client) if item["type"] == "deadline_reminder"]

    waiting = await reminders("student@example.com")
    late = await reminders("late@example.com")
    submitted = await reminders("submitted@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    teacher = [item for item in await notifications(client) if item["type"] == "deadline_reminder"]

    assert (first_run, second_run) == (1, 0)
    assert len(waiting) == len(late) == 1
    assert waiting[0]["title"] == "Скоро дедлайн"
    assert waiting[0]["text"].startswith("«Скоро» — до ")
    assert waiting[0]["text"].endswith("(МСК)")
    assert waiting[0]["target"]["assignment_id"] == due["id"]
    assert submitted == [] and teacher == []

    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    assert await scheduler.remind_deadlines() == 0
