from datetime import datetime
from urllib.parse import unquote

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course, CourseMaterialFile
from src.core.s3.service import S3Storage
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.files import download, is_in_s3, s3_unavailable, upload_to_s3


async def upload_file(
    client: AsyncClient, course_id: str, content: bytes, file_name: str = "Учебник.pdf"
) -> dict[str, str]:
    """Загружает файл в S3 по форме бэкенда; возвращает ссылку на него для материала."""
    started = await client.post(
        f"/api/courses/{course_id}/materials/uploads",
        json={"content_type": "application/pdf", "file_size": len(content)},
    )
    assert started.status_code == 200, started.text
    form = started.json()
    stored = await upload_to_s3(form, content, "application/pdf")
    assert stored.status_code == 204, stored.text
    return {"key": form["key"], "file_name": file_name}


async def create_material(
    client: AsyncClient, course_id: str, *contents: bytes, title: str = "Учебник"
) -> dict:
    files = [
        await upload_file(client, course_id, content, f"{index}.pdf")
        for index, content in enumerate(contents, start=1)
    ]
    created = await client.post(
        f"/api/courses/{course_id}/materials", json={"title": title, "files": files}
    )
    assert created.status_code == 201, created.text
    material: dict = created.json()
    return material


def changed_at(material: dict) -> datetime:
    return datetime.fromisoformat(material["updated_at"])


async def signed_in_teacher_course(client: AsyncClient, db: AsyncSession) -> dict:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")
    return await create_course(client, [group.id])


@pytest.mark.case(id="UC-T5-001")
async def test_teacher_creates_material(client: AsyncClient, db: AsyncSession) -> None:
    course = await signed_in_teacher_course(client, db)
    files = [
        await upload_file(client, course["id"], b"%PDF-1.7 book", "Учебник.pdf"),
        await upload_file(client, course["id"], b"rules", "Оформление.pdf"),
    ]

    response = await client.post(
        f"/api/courses/{course['id']}/materials",
        json={
            "title": " Оформление отчётов ",
            "text": "Шаблон: [ссылка](https://example.com/template)",
            "files": files,
        },
    )

    assert response.status_code == 201, response.text
    material = response.json()
    assert material["title"] == "Оформление отчётов"
    assert material["text"] == "Шаблон: [ссылка](https://example.com/template)"
    assert [
        (file["file_name"], file["file_size"], file["content_type"]) for file in material["files"]
    ] == [("Учебник.pdf", 13, "application/pdf"), ("Оформление.pdf", 5, "application/pdf")]
    file = await download(material["files"][0]["download_url"])
    assert file.status_code == 200
    assert file.content == b"%PDF-1.7 book"
    assert "Учебник.pdf" in unquote(file.headers["content-disposition"])

    text_only = await client.post(
        f"/api/courses/{course['id']}/materials",
        json={"title": "Полезные ссылки", "text": "https://example.com"},
    )
    assert text_only.status_code == 201, text_only.text
    assert text_only.json()["files"] == []


@pytest.mark.case(id="UC-T5-002")
async def test_material_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id])
    other = await create_course(client, [group.id], name="Другой курс")
    uploads = f"/api/courses/{course['id']}/materials/uploads"
    materials = f"/api/courses/{course['id']}/materials"

    no_title = await client.post(materials, json={"title": "  "})
    too_large = await client.post(
        uploads, json={"content_type": "application/pdf", "file_size": 20 * 1024 * 1024 + 1}
    )
    foreign_file = await upload_file(client, other["id"], b"abc")
    foreign = await client.post(materials, json={"title": "М", "files": [foreign_file]})
    own_form = (
        await client.post(uploads, json={"content_type": "text/plain", "file_size": 3})
    ).json()
    not_uploaded = await client.post(
        materials, json={"title": "М", "files": [{"key": own_form["key"], "file_name": "a"}]}
    )
    s3_over_limit = await upload_to_s3(own_form, b"x" * (20 * 1024 * 1024 + 1), "text/plain")
    twice = await upload_file(client, course["id"], b"abc")
    duplicate = await client.post(materials, json={"title": "М", "files": [twice, twice]})

    assert (no_title.status_code, error_code(no_title)) == (422, "request.invalid")
    assert (too_large.status_code, error_code(too_large)) == (422, "materials.file_too_large")
    assert (foreign.status_code, error_code(foreign)) == (422, "materials.foreign_file_key")
    assert (not_uploaded.status_code, error_code(not_uploaded)) == (
        422,
        "materials.file_not_uploaded",
    )
    assert s3_over_limit.status_code == 400
    assert (duplicate.status_code, error_code(duplicate)) == (
        409,
        "materials.file_already_attached",
    )
    assert (await client.get(materials)).json()["items"] == []

    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.post(uploads, json={"content_type": "text/plain", "file_size": 3})
    assert (archived.status_code, error_code(archived)) == (409, "materials.course_archived")

    await sign_in(client, "student@example.com", "password-1")
    student = await client.post(materials, json={"title": "М"})
    assert (student.status_code, error_code(student)) == (403, "materials.course_forbidden")


@pytest.mark.case(id="UC-T5-003")
async def test_deleted_material_leaves_s3(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id])
    other = await create_course(client, [group.id], name="Другой курс")
    material = await create_material(client, course["id"], b"first", b"second")

    wrong_course = await client.delete(f"/api/courses/{other['id']}/materials/{material['id']}")
    deleted = await client.delete(f"/api/courses/{course['id']}/materials/{material['id']}")

    assert (wrong_course.status_code, error_code(wrong_course)) == (404, "materials.not_found")
    assert deleted.status_code == 204
    listing = (await client.get(f"/api/courses/{course['id']}/materials")).json()
    assert listing["items"] == []
    for file in material["files"]:
        assert (await download(file["download_url"])).status_code == 404


@pytest.mark.case(id="UC-T5-004")
async def test_course_students_see_materials(client: AsyncClient, db: AsyncSession) -> None:
    own = await create_group(db, name="БВТ2601", code="CODE-1")
    other = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [own])
    await create_student(client, db, own, "CODE-1", "student@example.com")
    await create_student(client, db, other, "CODE-2", "outsider@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [own.id])
    first = await create_material(client, course["id"], b"first", title="Первый")
    second = await create_material(client, course["id"], b"second", title="Второй")
    url = f"/api/courses/{course['id']}/materials"

    await sign_in(client, "student@example.com", "password-1")
    page = (await client.get(url, params={"per_page": 1})).json()
    assert [m["id"] for m in page["items"]] == [second["id"]]
    assert (page["total"], page["pages"]) == (2, 2)
    last = (await client.get(url, params={"per_page": 1, "page": 2})).json()
    assert [m["id"] for m in last["items"]] == [first["id"]]
    assert (await download(last["items"][0]["files"][0]["download_url"])).content == b"first"

    await sign_in(client, "outsider@example.com", "password-1")
    outsider = await client.get(url)
    assert (outsider.status_code, error_code(outsider)) == (403, "materials.course_forbidden")


@pytest.mark.case(id="UC-T5-005")
async def test_material_survives_s3_failure(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    course = await signed_in_teacher_course(client, db)
    material = await create_material(client, course["id"], b"content")
    material_url = f"/api/courses/{course['id']}/materials/{material['id']}"
    monkeypatch.setattr(S3Storage, "delete", s3_unavailable)
    monkeypatch.setattr(S3Storage, "delete_many", s3_unavailable)

    whole = await client.delete(material_url)
    one_file = await client.delete(f"{material_url}/files/{material['files'][0]['id']}")

    assert (whole.status_code, error_code(whole)) == (503, "s3.unavailable")
    assert (one_file.status_code, error_code(one_file)) == (503, "s3.unavailable")
    listing = (await client.get(f"/api/courses/{course['id']}/materials")).json()
    [kept] = listing["items"]
    assert [file["id"] for file in kept["files"]] == [material["files"][0]["id"]]
    assert (await download(kept["files"][0]["download_url"])).content == b"content"


@pytest.mark.case(id="UC-T5-006")
async def test_material_is_edited(client: AsyncClient, db: AsyncSession) -> None:
    course = await signed_in_teacher_course(client, db)
    material = await create_material(client, course["id"], b"old")
    other = await create_material(client, course["id"], b"other", title="Другой")
    material_url = f"/api/courses/{course['id']}/materials/{material['id']}"

    edited = await client.put(material_url, json={"title": "Методичка", "text": "Новый текст"})
    added = await client.post(
        f"{material_url}/files", json=await upload_file(client, course["id"], b"new", "Новый.pdf")
    )
    foreign_file = await client.delete(f"{material_url}/files/{other['files'][0]['id']}")
    removed = await client.delete(f"{material_url}/files/{material['files'][0]['id']}")

    assert edited.status_code == 200, edited.text
    assert changed_at(edited.json()) > changed_at(material)
    assert (edited.json()["title"], edited.json()["text"]) == ("Методичка", "Новый текст")
    assert added.status_code == 201, added.text
    assert changed_at(added.json()) > changed_at(edited.json())
    assert [file["file_name"] for file in added.json()["files"]] == ["1.pdf", "Новый.pdf"]
    assert (foreign_file.status_code, error_code(foreign_file)) == (
        404,
        "materials.file_not_found",
    )
    assert removed.status_code == 204
    assert (await download(material["files"][0]["download_url"])).status_code == 404
    listing = (await client.get(f"/api/courses/{course['id']}/materials")).json()
    kept = next(item for item in listing["items"] if item["id"] == material["id"])
    assert [file["file_name"] for file in kept["files"]] == ["Новый.pdf"]
    assert changed_at(kept) > changed_at(added.json())


@pytest.mark.case(id="UC-T5-007")
async def test_rejected_material_discards_uploaded_files(
    client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id])
    other = await create_course(client, [group.id], name="Другой курс")
    materials = f"/api/courses/{course['id']}/materials"
    await create_material(client, course["id"], b"kept")
    attached = await db.scalar(select(CourseMaterialFile.file_key))
    assert attached is not None
    foreign = await upload_file(client, other["id"], b"foreign")
    fresh = await upload_file(client, course["id"], b"fresh")
    for_archive = await upload_file(client, course["id"], b"for-archive")

    duplicate = await client.post(
        materials, json={"title": "М", "files": [{"key": attached, "file_name": "a"}, fresh]}
    )
    foreign_rejected = await client.post(materials, json={"title": "М", "files": [foreign]})
    await db.execute(update(Course).where(Course.id == course["id"]).values(is_archived=True))
    await db.commit()
    archived = await client.post(materials, json={"title": "М", "files": [for_archive]})

    assert (duplicate.status_code, foreign_rejected.status_code) == (409, 422)
    assert archived.status_code == 409
    assert await is_in_s3(attached)
    assert await is_in_s3(foreign["key"])
    assert not await is_in_s3(fresh["key"])
    assert not await is_in_s3(for_archive["key"])
