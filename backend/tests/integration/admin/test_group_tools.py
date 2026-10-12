import re

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Group, GroupInvite, User
from tests.support.admin import create_structure, signed_in_admin
from tests.support.auth import InvitedStudent, create_group, error_code, invite, login, register
from tests.support.courses import create_course, create_teacher, sign_in


def listed(text: str) -> set[str]:
    """Названия групп в таблице списка."""
    return set(re.findall(r"[БСМ][А-Я]{2}\d{4}", text))


async def another_client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def group_list(client: AsyncClient, **params: str) -> set[str]:
    response = await client.get("/admin/group/list", params={"pageSize": "100", **params})
    assert response.status_code == 200, response.text
    return listed(response.text)


@pytest.mark.case(id="ADMIN-GROUP-006")
async def test_groups_are_filtered_in_the_list(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    first = await create_structure(db, direction="ВТ")
    second = await create_structure(db, direction="ИС")
    await signed_in_admin(client, db)
    base = {
        "level": "bachelor",
        "study_form": "full_time",
        "admission_year": "2026",
        "name": "",
        "save": "Save",
    }
    for direction, number, level, form in [
        (first.direction_id, "1", "bachelor", "full_time"),
        (first.direction_id, "2", "master", "part_time"),
        (second.direction_id, "1", "bachelor", "full_time"),
    ]:
        response = await client.post(
            "/admin/group/create",
            data={
                **base,
                "direction": str(direction),
                "number": number,
                "level": level,
                "study_form": form,
            },
        )
        assert response.status_code == 200, response.text
    inactive = await db.scalar(select(Group).where(Group.name == "МВТ2602"))
    assert inactive is not None
    inactive.is_active = False
    teacher_group = await db.scalar(select(Group).where(Group.name == "БВТ2601"))
    assert teacher_group is not None
    await db.commit()
    await create_teacher(db, "teacher@example.com", "password-1", [teacher_group])
    async with await another_client(app) as teacher_client:
        await sign_in(teacher_client, "teacher@example.com", "password-1")
        course = await create_course(teacher_client, [teacher_group.id], term="autumn", year=2026)

    everything = await group_list(client)
    by_faculty = await group_list(client, faculty=str(first.faculty_id))
    by_direction = await group_list(client, direction=str(second.direction_id))
    by_level = await group_list(client, level="master")
    by_form = await group_list(client, study_form="part_time")
    only_inactive = await group_list(client, active="false")
    only_active = await group_list(client, active="true")
    in_course = await group_list(client, course=course["id"])
    forged = await client.get("/admin/group/list", params={"faculty": "not-a-uuid"})

    assert everything == {"БВТ2601", "МВТ2602", "БИС2601"}
    assert by_faculty == {"БВТ2601", "МВТ2602"}
    assert by_direction == {"БИС2601"}
    assert by_level == {"МВТ2602"}
    assert by_form == {"МВТ2602"}
    assert only_inactive == {"МВТ2602"}
    assert only_active == {"БВТ2601", "БИС2601"}
    assert in_course == {"БВТ2601"}
    assert forged.status_code == 200 and listed(forged.text) == set()


@pytest.mark.case(id="ADMIN-GROUP-007")
async def test_groups_are_created_in_a_batch(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db, direction="ВТ")
    await signed_in_admin(client, db)
    page = await client.get("/admin/groups-batch")
    form = {
        "direction": str(structure.direction_id),
        "level": "bachelor",
        "study_form": "full_time",
        "admission_year": "2026",
        "count": "3",
    }

    created = await client.post("/admin/groups-batch", data=form)
    codes = dict(
        re.findall(r"<tr><td>(БВТ\d{4})</td><td><code>([^<]+)</code></td></tr>", created.text)
    )
    names = (await db.scalars(select(Group.name).order_by(Group.name))).all()
    again = await client.post("/admin/groups-batch", data=form)
    overlapping = await client.post("/admin/groups-batch", data={**form, "count": "5"})
    too_many = await client.post("/admin/groups-batch", data={**form, "count": "31"})
    zero = await client.post("/admin/groups-batch", data={**form, "count": "0"})
    broken = await client.post("/admin/groups-batch", data={"count": "x"})
    total = await db.scalar(select(func.count()).select_from(Group))

    assert page.status_code == 200 and "Создать группы пачкой" in page.text
    assert created.status_code == 200, created.text
    assert created.headers["cache-control"].startswith("no-store")
    assert list(names) == ["БВТ2601", "БВТ2602", "БВТ2603"]
    assert sorted(codes) == ["БВТ2601", "БВТ2602", "БВТ2603"]
    assert len(set(codes.values())) == 3
    for response in (again, overlapping):
        assert "Группы с такими названиями уже есть" in response.text
        assert "БВТ2601" in response.text
    assert "БВТ2604" not in overlapping.text.split("уже есть")[1]
    assert "Количество групп вне допустимых границ" in too_many.text
    assert "Количество групп вне допустимых границ" in zero.text
    assert "Заполните все поля формы" in broken.text
    assert total == 3
    # Код каждой группы рабочий и разный.
    group = await db.scalar(select(Group).where(Group.name == "БВТ2602"))
    assert group is not None
    await invite(db, group, "student@example.com")
    student = InvitedStudent(group.id, codes["БВТ2602"], "student@example.com", "password-1")
    assert (await register(client, student)).status_code == 201


@pytest.mark.case(id="ADMIN-GROUP-008")
async def test_group_deactivation_with_or_without_students(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    other = await create_group(db, name="БВТ2602", code="CODE-2")
    group_id = group.id
    await invite(db, group, "kept@example.com")
    await invite(db, group, "gone@example.com")
    await invite(db, other, "other@example.com")
    for email, student_group, code in [
        ("kept@example.com", group, "CODE-1"),
        ("gone@example.com", group, "CODE-1"),
        ("other@example.com", other, "CODE-2"),
    ]:
        student_client = await another_client(app)
        async with student_client:
            await register(
                student_client, InvitedStudent(student_group.id, code, email, "password-1")
            )
    await signed_in_admin(client, db)

    async def is_active(email: str) -> bool:
        await db.rollback()
        return bool(await db.scalar(select(User.is_active).where(User.email == email)))

    async def group_active(name: str) -> bool:
        await db.rollback()
        return bool(await db.scalar(select(Group.is_active).where(Group.name == name)))

    only_group = await client.get("/admin/group/action/deactivate", params={"pks": str(group_id)})
    after_group = (await group_active("БВТ2601"), await is_active("kept@example.com"))
    activated = await client.get("/admin/group/action/activate", params={"pks": str(group_id)})
    with_students = await client.get(
        "/admin/group/action/deactivate-with-students", params={"pks": str(group_id)}
    )
    after_both = (
        await group_active("БВТ2601"),
        await is_active("kept@example.com"),
        await is_active("gone@example.com"),
        await is_active("other@example.com"),
    )
    reactivated = await client.get("/admin/group/action/activate", params={"pks": str(group_id)})
    forgotten = await client.get(
        "/admin/group/action/deactivate", params={"pks": "00000000-0000-7000-8000-000000000000"}
    )
    login_response = await login(client, "kept@example.com", "password-1")

    assert only_group.status_code == activated.status_code == with_students.status_code == 200
    assert after_group == (False, True)
    assert after_both == (False, False, False, True)
    assert "Групп деактивировано: 1" in with_students.text
    assert await group_active("БВТ2601") and not await is_active("kept@example.com")
    assert reactivated.status_code == 200
    assert login_response.status_code == 401
    assert error_code(login_response) == "auth.account_deactivated"
    assert "Группа не найдена" in forgotten.text


@pytest.mark.case(id="ADMIN-INVITE-004")
async def test_emails_are_imported_from_text_and_csv(client: AsyncClient, db: AsyncSession) -> None:
    group = await create_group(db, name="БВТ2601", code="CODE-1")
    other = await create_group(db, name="БВТ2602", code="CODE-2")
    await invite(db, other, "taken@example.com")
    await invite(db, group, "listed@example.com")
    await signed_in_admin(client, db)
    page = await client.get("/admin/invites-import")
    text = (
        "New1@Example.com, new2@example.com\nnot-an-email\nnew1@example.com\n"
        "taken@example.com;listed@example.com"
    )
    csv_file = (
        "email;ФИО\ncsv1@example.com;Иванов\ncsv2@example.com;Петров\n\ncsv1@example.com;Повтор\n"
    ).encode()

    imported = await client.post(
        "/admin/invites-import",
        data={"group": str(group.id), "emails": text},
        files={"csv": ("students.csv", csv_file, "text/csv")},
    )
    stored = (
        await db.scalars(select(GroupInvite.email).where(GroupInvite.group_id == group.id))
    ).all()
    no_group = await client.post("/admin/invites-import", data={"group": "", "emails": "a@b.co"})

    assert page.status_code == 200 and "Загрузить почты в группу" in page.text
    assert imported.status_code == 200, imported.text
    assert "Добавлено почт: 4" in imported.text
    assert sorted(stored) == [
        "csv1@example.com",
        "csv2@example.com",
        "listed@example.com",
        "new1@example.com",
        "new2@example.com",
    ]
    report = imported.text
    assert "Не похоже на почту (1)" in report and "not-an-email" in report
    assert "Повторяется в списке (2)" in report
    assert "Уже есть в списке одной из групп (2)" in report
    assert "taken@example.com" in report and "listed@example.com" in report
    assert "Выберите группу" in no_group.text
