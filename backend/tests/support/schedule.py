from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Group
from tests.support.auth import create_group
from tests.support.courses import create_course, create_student, create_teacher, sign_in


async def autumn_course(client: AsyncClient, db: AsyncSession) -> tuple[dict, Group]:
    """Курс в осеннем семестре 2026 (1 сентября – 31 января, пары до 30 декабря).

    Курс `teacher@example.com` с группой `БВТ2601` и студентом `student@example.com`
    (пароли `password-1`); в `client` — преподаватель.
    """
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    await create_student(client, db, group, "CODE-1", "student@example.com")
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id], term="autumn", year=2026)
    return course, group


def rule_body(group: Group, **fields: object) -> dict[str, object]:
    return {
        "group_id": str(group.id),
        "lesson_type": "lab",
        "weekday": 2,
        "slot": 1,
        "repeat": "weekly",
        "room": "Б-101",
        **fields,
    }


async def add_rule(client: AsyncClient, course_id: str, group: Group, **fields: object) -> dict:
    response = await client.post(
        f"/api/courses/{course_id}/schedule/rules", json=rule_body(group, **fields)
    )
    assert response.status_code == 201, response.text
    body: dict = response.json()
    return body


async def add_extra(
    client: AsyncClient, course_id: str, group: Group, day: str, **fields: object
) -> Response:
    return await client.post(
        f"/api/courses/{course_id}/schedule/extras",
        json={
            "group_id": str(group.id),
            "lesson_type": "practice",
            "day": day,
            "slot": 4,
            "room": None,
            **fields,
        },
    )


async def assign_exam(
    client: AsyncClient,
    course_id: str,
    group: Group,
    exam_type: str = "exam",
    day: str = "2027-01-12",
    slot: int = 2,
) -> dict:
    """Назначает группе зачёт, дифф. зачёт или экзамен."""
    response = await client.post(
        f"/api/courses/{course_id}/exams",
        json={
            "group_id": str(group.id),
            "exam_type": exam_type,
            "day": day,
            "slot": slot,
            "room": None,
        },
    )
    assert response.status_code == 201, response.text
    body: dict = response.json()
    return body
