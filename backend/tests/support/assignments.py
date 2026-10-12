from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.auth import create_group
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.files import upload_to_s3


async def course_with_student(client: AsyncClient, db: AsyncSession, **fields: object) -> dict:
    """Курс `teacher@example.com` с группой `БВТ2601` и студентом `student@example.com`
    (пароли `password-1`); в `client` — преподаватель."""
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    return await create_course(client, [group.id], **fields)


def assignment_body(**fields: object) -> dict[str, object]:
    return {
        "type": "lab",
        "title": "Сортировки",
        "description": "Реализовать quicksort",
        "deadline_type": "none",
        "deadline_at": None,
        "scale": None,
        "grading_note": "3 — работает, 5 — с тестами",
        **fields,
    }


async def create_assignment(client: AsyncClient, course_id: str, **fields: object) -> dict:
    response = await client.post(
        f"/api/courses/{course_id}/assignments", json=assignment_body(**fields)
    )
    assert response.status_code == 201, response.text
    body: dict = response.json()
    return body


async def upload(client: AsyncClient, uploads_url: str, content: bytes, name: str) -> dict:
    """Загружает файл по форме бэкенда; возвращает ссылку на него для записи."""
    started = await client.post(
        uploads_url, json={"content_type": "application/pdf", "file_size": len(content)}
    )
    assert started.status_code == 200, started.text
    form = started.json()
    stored = await upload_to_s3(form, content, "application/pdf")
    assert stored.status_code == 204, stored.text
    return {"key": form["key"], "file_name": name}


def submissions_url(course_id: str, assignment_id: str) -> str:
    return f"/api/courses/{course_id}/assignments/{assignment_id}/submissions"


async def submit(
    client: AsyncClient,
    course_id: str,
    assignment_id: str,
    comment: str | None = "Готово",
    *contents: bytes,
) -> Response:
    url = submissions_url(course_id, assignment_id)
    files = [
        await upload(client, f"{url}/uploads", content, f"{index}.pdf")
        for index, content in enumerate(contents, start=1)
    ]
    return await client.post(url, json={"comment": comment, "files": files})


async def review(
    client: AsyncClient,
    course_id: str,
    assignment_id: str,
    submission_id: str,
    verdict: str,
    **grade: object,
) -> Response:
    return await client.post(
        f"{submissions_url(course_id, assignment_id)}/{submission_id}/review",
        json={"verdict": verdict, "grade": grade, "comment": "Комментарий"},
    )
