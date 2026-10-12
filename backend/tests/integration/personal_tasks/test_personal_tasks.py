import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import create_group, error_code
from tests.support.courses import create_student, create_teacher, sign_in


def task_body(**fields: object) -> dict[str, object]:
    return {"title": "Начать графы", "due_date": "2026-10-16", "due_time": None, **fields}


@pytest.mark.case(id="UC-S7-001")
async def test_student_keeps_personal_tasks(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "student@example.com")

    created = await client.post("/api/personal-tasks", json=task_body(title=" Сдать отчёт "))
    timed = await client.post(
        "/api/personal-tasks", json=task_body(title="Лекция", due_time="09:30:00")
    )
    later = await client.post("/api/personal-tasks", json=task_body(due_date="2026-10-20"))
    task = created.json()
    done = await client.patch(f"/api/personal-tasks/{task['id']}/done", json={"is_done": True})
    edited = await client.put(
        f"/api/personal-tasks/{task['id']}",
        json=task_body(title="Сдать отчёт по БД", due_date="2026-10-17", due_time="12:00:00"),
    )
    listed = await client.get(
        "/api/personal-tasks", params={"from": "2026-10-16", "to": "2026-10-17"}
    )
    deleted = await client.delete(f"/api/personal-tasks/{later.json()['id']}")
    wide = await client.get(
        "/api/personal-tasks", params={"from": "2026-10-01", "to": "2026-10-31"}
    )

    assert created.status_code == 201, created.text
    assert (task["title"], task["is_done"], task["due_time"]) == ("Сдать отчёт", False, None)
    assert done.json()["is_done"] is True
    assert (edited.json()["title"], edited.json()["due_date"], edited.json()["due_time"]) == (
        "Сдать отчёт по БД",
        "2026-10-17",
        "12:00:00",
    )
    assert edited.json()["is_done"] is True
    # Задачи без времени идут первыми в своём дне.
    assert [item["title"] for item in listed.json()["items"]] == ["Лекция", "Сдать отчёт по БД"]
    assert deleted.status_code == 204
    assert [item["title"] for item in wide.json()["items"]] == ["Лекция", "Сдать отчёт по БД"]
    assert timed.status_code == 201


@pytest.mark.case(id="UC-S7-002")
async def test_personal_tasks_are_private_and_validated(
    client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "first@example.com")
    mine = (await client.post("/api/personal-tasks", json=task_body())).json()
    await create_student(client, db, group, "CODE-1", "second@example.com")

    foreign_edit = await client.put(f"/api/personal-tasks/{mine['id']}", json=task_body())
    foreign_done = await client.patch(
        f"/api/personal-tasks/{mine['id']}/done", json={"is_done": True}
    )
    foreign_delete = await client.delete(f"/api/personal-tasks/{mine['id']}")
    foreign_list = await client.get(
        "/api/personal-tasks", params={"from": "2026-10-01", "to": "2026-10-31"}
    )
    empty_title = await client.post("/api/personal-tasks", json=task_body(title="  "))
    long_title = await client.post("/api/personal-tasks", json=task_body(title="я" * 201))
    reversed_range = await client.get(
        "/api/personal-tasks", params={"from": "2026-10-31", "to": "2026-10-01"}
    )
    too_long = await client.get(
        "/api/personal-tasks", params={"from": "2026-01-01", "to": "2027-12-31"}
    )

    for response in (foreign_edit, foreign_done, foreign_delete):
        assert (response.status_code, error_code(response)) == (404, "personal_tasks.not_found")
    assert foreign_list.json()["items"] == []
    for response in (empty_title, long_title):
        assert (response.status_code, error_code(response)) == (422, "request.invalid")
    for response in (reversed_range, too_long):
        assert (response.status_code, error_code(response)) == (
            422,
            "personal_tasks.invalid_range",
        )

    await sign_in(client, "teacher@example.com", "password-1")
    teacher = await client.post("/api/personal-tasks", json=task_body())
    assert (teacher.status_code, error_code(teacher)) == (403, "personal_tasks.student_only")
