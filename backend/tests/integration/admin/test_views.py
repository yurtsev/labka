from uuid import uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserRole
from src.core.db.models import GroupInvite, TeacherGroup, User
from tests.support.admin import create_structure, signed_in_admin
from tests.support.auth import create_group


@pytest.mark.case(id="ADMIN-VIEWS-001")
async def test_every_section_renders_with_data(client: AsyncClient, db: AsyncSession) -> None:
    structure = await create_structure(db)
    group = await create_group(db, name="БВТ2601", code="GROUP-CODE-1")
    invite = GroupInvite(id=uuid7(), group_id=group.id, email="student@example.com")
    teacher = User(
        id=uuid7(),
        last_name="Петров",
        first_name="Пётр",
        email="teacher@example.com",
        password_hash="argon2-hash-must-not-leak",
        role=UserRole.TEACHER,
        department_id=structure.department_id,
    )
    db.add_all([invite, teacher])
    await db.flush()
    db.add(TeacherGroup(teacher_id=teacher.id, group_id=group.id))
    await db.commit()
    await signed_in_admin(client, db)
    sections = {
        "faculty": structure.faculty_id,
        "department": structure.department_id,
        "direction": structure.direction_id,
        "group": group.id,
        "group-invite": invite.id,
        "teacher": teacher.id,
    }

    for identity, pk in sections.items():
        for path in ("list", f"details/{pk}", f"edit/{pk}", "export/csv"):
            response = await client.get(f"/admin/{identity}/{path}")
            assert response.status_code == 200, f"{identity}/{path}: {response.text[:300]}"
            assert "argon2-hash-must-not-leak" not in response.text
            assert group.registration_code_hash not in response.text
