from collections.abc import Collection
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.access.service import AccessService
from src.core.db.models import CourseGroup, Group
from tests.support.auth import create_group, error_code
from tests.support.courses import (
    create_course,
    create_student,
    create_teacher,
    get_course,
    sign_in,
)


@pytest.mark.case(id="UC-T4-001")
async def test_added_group_sees_course_removed_does_not(
    client: AsyncClient, db: AsyncSession
) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    await create_student(client, db, second, "CODE-2", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id])

    added = await client.post(
        f"/api/courses/{course['id']}/groups", json={"group_id": str(second.id)}
    )
    assert added.status_code == 200, added.text
    assert [group["name"] for group in added.json()["groups"]] == ["БВТ2601", "БВТ2602"]
    await sign_in(client, "student@example.com", "password-1")
    assert (await get_course(client, course["id"])).status_code == 200
    assert [c["id"] for c in (await client.get("/api/courses")).json()["items"]] == [course["id"]]

    await sign_in(client, "teacher@example.com", "password-1")
    removed = await client.delete(f"/api/courses/{course['id']}/groups/{second.id}")
    assert removed.status_code == 200, removed.text
    assert [group["name"] for group in removed.json()["groups"]] == ["БВТ2601"]
    await sign_in(client, "student@example.com", "password-1")
    assert (await get_course(client, course["id"])).status_code == 403
    assert (await client.get("/api/courses")).json()["items"] == []


@pytest.mark.case(id="UC-T4-002")
async def test_group_changes_are_validated(client: AsyncClient, db: AsyncSession) -> None:
    attached = await create_group(db, name="БВТ2601", code="CODE-1")
    foreign = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [attached])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [attached.id])
    groups_url = f"/api/courses/{course['id']}/groups"

    not_attached = await client.post(groups_url, json={"group_id": str(foreign.id)})
    twice = await client.post(groups_url, json={"group_id": str(attached.id)})
    absent = await client.delete(f"{groups_url}/{foreign.id}")

    assert (not_attached.status_code, error_code(not_attached)) == (
        422,
        "courses.group_not_available",
    )
    assert (twice.status_code, error_code(twice)) == (409, "courses.group_already_in_course")
    assert (absent.status_code, error_code(absent)) == (404, "courses.group_not_in_course")


@pytest.mark.case(id="UC-T4-003")
async def test_available_groups_are_searchable(client: AsyncClient, db: AsyncSession) -> None:
    vt = await create_group(db, name="БВТ2601", code="CODE-1")
    pi = await create_group(db, name="БПИ2601", code="CODE-2")
    old = await create_group(db, name="БВТ2201", code="CODE-3")
    inactive = await create_group(db, name="БВТ2602", code="CODE-4", is_active=False)
    await create_group(db, name="БВТ2603", code="CODE-5")
    await db.execute(update(Group).where(Group.id == old.id).values(admission_year=2022))
    await db.commit()
    await create_teacher(db, "teacher@example.com", "password-1", [vt, pi, old, inactive])
    await sign_in(client, "teacher@example.com", "password-1")
    url = "/api/courses/available-groups"

    async def names(**params: str | int) -> list[str]:
        response = await client.get(url, params=params)
        assert response.status_code == 200, response.text
        return [group["name"] for group in response.json()["items"]]

    assert await names() == ["БВТ2201", "БВТ2601", "БПИ2601"]
    assert await names(query="вт") == ["БВТ2201", "БВТ2601"]
    assert await names(query="вт", admission_year=2022) == ["БВТ2201"]
    assert await names(query="%") == []
    second = (await client.get(url, params={"page": 2, "per_page": 2})).json()
    assert [g["name"] for g in second["items"]] == ["БПИ2601"]
    assert (second["total"], second["pages"]) == (3, 2)


@pytest.mark.case(id="UC-T4-004")
async def test_concurrent_group_addition_is_conflict(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id])
    attachable_groups = AccessService.attachable_groups

    async def added_concurrently(
        self: AccessService, teacher_id: UUID, group_ids: Collection[UUID]
    ) -> list[Group]:
        # Параллельный запрос успевает добавить группу между проверкой и commit.
        db.add(CourseGroup(course_id=UUID(course["id"]), group_id=second.id))
        await db.commit()
        return await attachable_groups(self, teacher_id, group_ids)

    monkeypatch.setattr(AccessService, "attachable_groups", added_concurrently)
    response = await client.post(
        f"/api/courses/{course['id']}/groups", json={"group_id": str(second.id)}
    )

    assert (response.status_code, error_code(response)) == (
        409,
        "courses.group_already_in_course",
    )
