import re
from uuid import UUID, uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import GroupInvite, User
from tests.support.admin import signed_in_admin
from tests.support.auth import InvitedStudent, create_group, error_code, login, register
from tests.support.courses import create_course, create_teacher, sign_in


async def another_client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def enroll(app: FastAPI, db: AsyncSession, group_id: UUID, code: str, email: str) -> UUID:
    """Регистрирует студента группы и возвращает его id."""
    db.add(GroupInvite(id=uuid7(), group_id=group_id, email=email))
    await db.commit()
    async with await another_client(app) as student_client:
        response = await register(
            student_client, InvitedStudent(group_id, code, email, "password-1")
        )
        assert response.status_code == 201, response.text
    return await user_id(db, email)


async def user_id(db: AsyncSession, email: str) -> UUID:
    await db.rollback()
    found = await db.scalar(select(User.id).where(User.email == email))
    assert found is not None
    return found


def passwords(text: str) -> dict[str, str]:
    """Пары «почта — пароль» со страницы новых паролей."""
    rows = re.findall(r"<td>([^<@]+@[^<]+)</td>\s*<td><code>([^<]+)</code></td>", text)
    return dict(rows)


def emails(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+@example\.com", text))


@pytest.mark.case(id="ADMIN-USER-001")
async def test_students_are_listed_filtered_and_searched(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    first_id, second_id = first.id, second.id
    await create_teacher(db, "teacher@example.com", "password-1", [first])
    await enroll(app, db, first_id, "CODE-1", "alpha@example.com")
    beta = await enroll(app, db, first_id, "CODE-1", "beta@example.com")
    await enroll(app, db, second_id, "CODE-2", "gamma@example.com")
    await signed_in_admin(client, db)
    await client.get("/admin/student/action/deactivate", params={"pks": str(beta)})

    async def students(**params: str) -> set[str]:
        response = await client.get("/admin/student/list", params={"pageSize": "100", **params})
        assert response.status_code == 200, response.text
        return emails(response.text)

    everyone = await students()
    by_group = await students(group=str(first_id))
    inactive = await students(active="false")
    active_in_group = await students(group=str(first_id), active="true")
    searched = await students(search="gamma")
    forged = await students(group="not-a-uuid")
    create = await client.get("/admin/student/create")
    edit = await client.get(f"/admin/student/edit/{beta}")
    teacher_as_student = await client.get(
        "/admin/student/details/" + str(await user_id(db, "teacher@example.com"))
    )

    assert everyone == {"alpha@example.com", "beta@example.com", "gamma@example.com"}
    assert by_group == {"alpha@example.com", "beta@example.com"}
    assert inactive == {"beta@example.com"}
    assert active_in_group == {"alpha@example.com"}
    assert searched == {"gamma@example.com"}
    assert forged == set()
    assert create.status_code == edit.status_code == 403
    assert teacher_as_student.status_code == 404
    assert "teacher@example.com" not in "".join(everyone)


@pytest.mark.case(id="ADMIN-USER-002")
async def test_deactivation_ends_sessions_and_blocks_login(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    group_id = group.id
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    first = await enroll(app, db, group_id, "CODE-1", "first@example.com")
    second = await enroll(app, db, group_id, "CODE-1", "second@example.com")
    teacher = await user_id(db, "teacher@example.com")
    await signed_in_admin(client, db)
    async with await another_client(app) as student_one, await another_client(app) as staff:
        await login(student_one, "first@example.com", "password-1")
        await login(staff, "teacher@example.com", "password-1")
        before = (await student_one.get("/api/auth/me")).status_code

        many = await client.get(
            "/admin/student/action/deactivate", params={"pks": f"{first},{second}"}
        )
        teacher_off = await client.get(
            "/admin/teacher/action/deactivate", params={"pks": str(teacher)}
        )
        student_session = await student_one.get("/api/auth/me")
        teacher_session = await staff.get("/api/auth/me")
        blocked = await login(student_one, "first@example.com", "password-1")
        wrong_role = await client.get(
            "/admin/student/action/deactivate", params={"pks": str(teacher)}
        )
        on = await client.get("/admin/student/action/activate", params={"pks": str(first)})
        teacher_on = await client.get(
            "/admin/teacher/action/activate", params={"pks": str(teacher)}
        )
        back = await login(student_one, "first@example.com", "password-1")
        still_off = await login(student_one, "second@example.com", "password-1")
        teacher_back = await login(staff, "teacher@example.com", "password-1")

    assert before == 200
    assert "Пользователей деактивировано: 2" in many.text
    assert "Их сессии завершены" in many.text
    assert "Пользователей деактивировано: 1" in teacher_off.text
    assert student_session.status_code == teacher_session.status_code == 401
    assert (blocked.status_code, error_code(blocked)) == (401, "auth.account_deactivated")
    assert "Выбранных пользователей нет" in wrong_role.text
    assert "Пользователей активировано: 1" in on.text
    assert on.status_code == teacher_on.status_code == 200
    assert back.status_code == 200 and teacher_back.status_code == 200
    assert error_code(still_off) == "auth.account_deactivated"


@pytest.mark.case(id="ADMIN-USER-003")
async def test_password_reset_shows_new_passwords_once(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    group_id = group.id
    await create_teacher(db, "teacher@example.com", "password-1", [group])
    first = await enroll(app, db, group_id, "CODE-1", "first@example.com")
    second = await enroll(app, db, group_id, "CODE-1", "second@example.com")
    teacher = await user_id(db, "teacher@example.com")
    await signed_in_admin(client, db)
    async with await another_client(app) as student, await another_client(app) as staff:
        await login(student, "first@example.com", "password-1")
        await login(staff, "teacher@example.com", "password-1")

        reset = await client.get(
            "/admin/student/action/reset-password", params={"pks": f"{first},{second}"}
        )
        teacher_reset = await client.get(
            "/admin/teacher/action/reset-password", params={"pks": str(teacher)}
        )
        new_student = passwords(reset.text)
        new_teacher = passwords(teacher_reset.text)
        old_session = await student.get("/api/auth/me")
        old_password = await login(student, "first@example.com", "password-1")
        new_login = await login(student, "first@example.com", new_student["first@example.com"])
        teacher_old = await login(staff, "teacher@example.com", "password-1")
        teacher_new = await login(staff, "teacher@example.com", new_teacher["teacher@example.com"])
        nobody = await client.get(
            "/admin/student/action/reset-password",
            params={"pks": "00000000-0000-7000-8000-000000000000"},
        )

    assert reset.status_code == 200 and reset.headers["cache-control"].startswith("no-store")
    assert set(new_student) == {"first@example.com", "second@example.com"}
    assert set(new_teacher) == {"teacher@example.com"}
    assert len(set(new_student.values()) | set(new_teacher.values())) == 3
    assert old_session.status_code == 401
    assert old_password.status_code == teacher_old.status_code == 401
    assert new_login.status_code == teacher_new.status_code == 200
    assert "Выбранных пользователей нет" in nobody.text
    assert "password-1" not in reset.text


@pytest.mark.case(id="ADMIN-USER-004")
async def test_students_are_transferred_to_another_group(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    old = await create_group(db, name="БВТ2601", code="CODE-1")
    new = await create_group(db, name="БВТ2602", code="CODE-2")
    closed = await create_group(db, name="БВТ2603", code="CODE-3", is_active=False)
    old_id, new_id, closed_id = old.id, new.id, closed.id
    await create_teacher(db, "teacher@example.com", "password-1", [old, new])
    mover = await enroll(app, db, old_id, "CODE-1", "mover@example.com")
    stayer = await enroll(app, db, old_id, "CODE-1", "stayer@example.com")
    teacher = await user_id(db, "teacher@example.com")
    async with await another_client(app) as staff:
        await sign_in(staff, "teacher@example.com", "password-1")
        old_course = await create_course(
            staff, [old_id], name="Старый курс", term="autumn", year=2026
        )
        new_course = await create_course(
            staff, [new_id], name="Новый курс", term="autumn", year=2026
        )
    await signed_in_admin(client, db)

    redirect = await client.get(
        "/admin/student/action/transfer",
        params={"pks": f"{mover},{stayer}"},
        follow_redirects=False,
    )
    page = await client.get("/admin/students-transfer", params={"pks": str(mover)})
    to_closed = await client.post(
        "/admin/students-transfer",
        params={"pks": str(mover)},
        data={"group": str(closed_id), "pks": str(mover)},
    )
    teacher_pk = await client.post(
        "/admin/students-transfer", params={"pks": str(teacher)}, data={"group": str(new_id)}
    )
    no_group = await client.post("/admin/students-transfer", params={"pks": str(mover)}, data={})
    moved = await client.post(
        "/admin/students-transfer", params={"pks": str(mover)}, data={"group": str(new_id)}
    )
    async with (
        await another_client(app) as moved_client,
        await another_client(app) as stayed_client,
    ):
        await login(moved_client, "mover@example.com", "password-1")
        await login(stayed_client, "stayer@example.com", "password-1")
        moved_courses = (await moved_client.get("/api/courses")).json()["items"]
        stayed_courses = (await stayed_client.get("/api/courses")).json()["items"]
        profile = (await moved_client.get("/api/profile")).json()

    assert redirect.status_code == 302
    assert redirect.headers["location"].endswith(f"/admin/students-transfer?pks={mover}%2C{stayer}")
    assert (
        page.status_code == 200 and "mover" not in page.text.lower() or "Новая группа" in page.text
    )
    assert "БВТ2601" in page.text and "БВТ2603" not in page.text
    assert "Нельзя перевести студентов в неактивную группу" in to_closed.text
    assert "Выбранных пользователей нет" in teacher_pk.text
    assert "Выберите группу" in no_group.text
    assert "Студентов переведено: 1" in moved.text
    assert [c["id"] for c in moved_courses] == [new_course["id"]]
    assert [c["id"] for c in stayed_courses] == [old_course["id"]]
    assert profile["group"]["name"] == "БВТ2602"
