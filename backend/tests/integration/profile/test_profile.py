import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Department, User
from src.core.s3.service import S3Storage
from tests.support.auth import create_group, error_code
from tests.support.courses import create_student, create_teacher, sign_in
from tests.support.files import download, is_in_s3, s3_unavailable, upload_to_s3


async def upload_avatar(
    client: AsyncClient, content: bytes, content_type: str = "image/png"
) -> str:
    started = await client.post(
        "/api/profile/avatar/uploads",
        json={"content_type": content_type, "file_size": len(content)},
    )
    assert started.status_code == 200, started.text
    form = started.json()
    assert (await upload_to_s3(form, content, content_type)).status_code == 204
    key: str = form["key"]
    return key


@pytest.mark.case(id="PROFILE-001")
async def test_profile_shows_affiliation(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "student@example.com")

    student = (await client.get("/api/profile")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    teacher = (await client.get("/api/profile")).json()

    assert (student["email"], student["last_name"], student["role"]) == (
        "student@example.com",
        "Иванов",
        "student",
    )
    assert student["group"] == {"id": str(group.id), "name": "БВТ2601"}
    assert student["department"] is None
    assert student["avatar_url"] is None
    department = await db.scalar(select(Department).join(User, User.department_id == Department.id))
    assert department is not None
    assert teacher["department"] == {"id": str(department.id), "name": department.name}
    assert teacher["group"] is None


@pytest.mark.case(id="UC-C5-001")
async def test_avatar_is_set_replaced_and_removed(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "student@example.com")

    first_key = await upload_avatar(client, b"first-png")
    first = await client.put("/api/profile/avatar", json={"key": first_key})
    assert first.status_code == 200, first.text
    first_url = first.json()["avatar_url"]
    assert (await download(first_url)).content == b"first-png"

    second_key = await upload_avatar(client, b"second-png")
    second = (await client.put("/api/profile/avatar", json={"key": second_key})).json()
    assert (await download(second["avatar_url"])).content == b"second-png"
    assert (await download(first_url)).status_code == 404

    removed = (await client.delete("/api/profile/avatar")).json()
    assert removed["avatar_url"] is None
    assert (await download(second["avatar_url"])).status_code == 404


@pytest.mark.case(id="UC-C5-002")
async def test_avatar_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "other@example.com")
    foreign_key = await upload_avatar(client, b"other-png")
    await create_student(client, db, group, "CODE-1", "student@example.com")

    not_image = await client.post(
        "/api/profile/avatar/uploads", json={"content_type": "application/pdf", "file_size": 3}
    )
    svg = await client.post(
        "/api/profile/avatar/uploads", json={"content_type": "image/svg+xml", "file_size": 3}
    )
    too_large = await client.post(
        "/api/profile/avatar/uploads",
        json={"content_type": "image/png", "file_size": 20 * 1024 * 1024 + 1},
    )
    foreign = await client.put("/api/profile/avatar", json={"key": foreign_key})
    form = (
        await client.post(
            "/api/profile/avatar/uploads", json={"content_type": "image/png", "file_size": 3}
        )
    ).json()
    not_uploaded = await client.put("/api/profile/avatar", json={"key": form["key"]})

    assert (not_image.status_code, error_code(not_image)) == (422, "profile.avatar_not_image")
    assert (svg.status_code, error_code(svg)) == (422, "profile.avatar_not_image")
    assert (too_large.status_code, error_code(too_large)) == (422, "profile.avatar_too_large")
    assert (foreign.status_code, error_code(foreign)) == (422, "profile.foreign_avatar_key")
    assert (not_uploaded.status_code, error_code(not_uploaded)) == (
        422,
        "profile.avatar_not_uploaded",
    )


@pytest.mark.case(id="UC-C5-003")
async def test_avatar_survives_s3_failure(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "student@example.com")
    first_key = await upload_avatar(client, b"first-png")
    assert (await client.put("/api/profile/avatar", json={"key": first_key})).status_code == 200
    second_key = await upload_avatar(client, b"second-png")
    monkeypatch.setattr(S3Storage, "delete", s3_unavailable)

    replaced = await client.put("/api/profile/avatar", json={"key": second_key})
    removed = await client.delete("/api/profile/avatar")

    assert (replaced.status_code, error_code(replaced)) == (503, "s3.unavailable")
    assert (removed.status_code, error_code(removed)) == (503, "s3.unavailable")
    profile = (await client.get("/api/profile")).json()
    assert (await download(profile["avatar_url"])).content == b"first-png"


@pytest.mark.case(id="UC-C5-004")
async def test_failed_avatar_replacement_discards_new_file(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_student(client, db, group, "CODE-1", "student@example.com")
    current_key = await upload_avatar(client, b"current-png")
    assert (await client.put("/api/profile/avatar", json={"key": current_key})).status_code == 200
    replaced_key = await upload_avatar(client, b"replaced-png")

    repeated = await client.put("/api/profile/avatar", json={"key": current_key})
    with monkeypatch.context() as patch:
        patch.setattr(S3Storage, "delete", s3_unavailable)
        unavailable = await client.put("/api/profile/avatar", json={"key": replaced_key})

    assert repeated.status_code == 200
    assert unavailable.status_code == 503
    assert await is_in_s3(current_key)
    assert not await is_in_s3(replaced_key)
