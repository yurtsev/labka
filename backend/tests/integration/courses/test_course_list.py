import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import create_group
from tests.support.courses import create_course, create_teacher, sign_in


@pytest.mark.case(id="UC-T2-005")
async def test_course_list_is_paginated(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")
    created = [(await create_course(client, [group.id], name=f"Курс {i}"))["id"] for i in range(5)]

    pages = [
        (await client.get("/api/courses", params={"page": page, "per_page": 2})).json()
        for page in (1, 2, 3, 4)
    ]

    assert [c["id"] for page in pages for c in page["items"]] == created[::-1]
    assert [(p["page"], p["per_page"], p["total"], p["pages"]) for p in pages] == [
        (1, 2, 5, 3),
        (2, 2, 5, 3),
        (3, 2, 5, 3),
        (4, 2, 5, 3),
    ]
    assert pages[3]["items"] == []
    assert set(pages[0]["items"][0]) == {
        "id",
        "name",
        "teacher",
        "is_archived",
        "groups",
        "pending_reviews",
    }
    assert pages[0]["items"][0]["pending_reviews"] == 0
    empty = (await client.get("/api/courses", params={"archived": True})).json()
    assert (empty["items"], empty["total"], empty["pages"]) == ([], 0, 1)
    for params in ({"per_page": 0}, {"per_page": 101}, {"page": 0}):
        assert (await client.get("/api/courses", params=params)).status_code == 422
