import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Course, User
from tests.support.auth import create_group, error_code
from tests.support.courses import create_course, create_student, create_teacher, sign_in
from tests.support.schedule import assign_exam, autumn_course


async def student_id(client: AsyncClient) -> str:
    profile = (await client.get("/api/profile")).json()
    return str(profile["id"])


@pytest.mark.case(id="UC-T17-001")
async def test_teacher_sets_and_corrects_final_grades(
    client: AsyncClient, db: AsyncSession
) -> None:
    course, group = await autumn_course(client, db)
    await sign_in(client, "student@example.com", "password-1")
    student = await student_id(client)
    await sign_in(client, "teacher@example.com", "password-1")
    await assign_exam(client, course["id"], group, "exam")
    url = f"/api/courses/{course['id']}/final-grades"

    before = (await client.get(url)).json()
    set_grade = await client.put(f"{url}/{student}", json={"grade": 3})
    corrected = await client.put(f"{url}/{student}", json={"grade": 5})
    after = (await client.get(url)).json()
    cleared = await client.delete(f"{url}/{student}")
    again = await client.delete(f"{url}/{student}")
    empty = (await client.get(url)).json()

    first = before["items"][0]
    assert (before["total"], first["exam_type"], first["grade"], first["passed"]) == (
        1,
        "exam",
        None,
        None,
    )
    assert first["graded_at"] is None
    assert set_grade.status_code == 200, set_grade.text
    assert (set_grade.json()["grade"], set_grade.json()["group_name"]) == (3, "БВТ2601")
    assert (set_grade.json()["passed"], set_grade.json()["exam_type"]) == (None, "exam")
    assert corrected.json()["grade"] == 5
    assert [(item["student_id"], item["grade"]) for item in after["items"]] == [(student, 5)]
    assert after["items"][0]["graded_at"] is not None
    assert cleared.status_code == 204
    assert (again.status_code, error_code(again)) == (404, "final_grades.not_found")
    assert empty["items"][0]["grade"] is None


@pytest.mark.case(id="UC-T17-002")
async def test_final_grade_is_validated(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    stranger_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, stranger_group, "CODE-2", "stranger@example.com")
    stranger = await student_id(client)
    await sign_in(client, "student@example.com", "password-1")
    student = await student_id(client)
    url = f"/api/courses/{course['id']}/final-grades"

    student_put = await client.put(f"{url}/{student}", json={"grade": 5})
    student_list = await client.get(url)
    await sign_in(client, "teacher@example.com", "password-1")
    await assign_exam(client, course["id"], group, "exam")
    results = {
        grade: await client.put(f"{url}/{student}", json={"grade": grade}) for grade in (1, 2, 6)
    }
    not_a_number = await client.put(f"{url}/{student}", json={"grade": "5"})
    nothing = await client.put(f"{url}/{student}", json={})
    both = await client.put(f"{url}/{student}", json={"grade": 4, "passed": True})
    foreign = await client.put(f"{url}/{stranger}", json={"grade": 4})
    await db.execute(update(User).where(User.id == student).values(is_active=False))
    await db.commit()
    inactive = await client.put(f"{url}/{student}", json={"grade": 4})
    await db.execute(update(User).where(User.id == student).values(is_active=True))
    await db.execute(update(Course).values(is_archived=True))
    await db.commit()
    archived = await client.put(f"{url}/{student}", json={"grade": 4})

    for response in (student_put, student_list):
        assert (response.status_code, error_code(response)) == (
            403,
            "final_grades.course_forbidden",
        )
    assert results[2].status_code == 200
    for response in (results[1], results[6], not_a_number, nothing, both):
        assert (response.status_code, error_code(response)) == (422, "request.invalid")
    for response in (foreign, inactive):
        assert (response.status_code, error_code(response)) == (
            404,
            "final_grades.student_not_in_course",
        )
    assert (archived.status_code, error_code(archived)) == (409, "final_grades.course_archived")


@pytest.mark.case(id="UC-T17-003")
async def test_final_grades_table_is_paged_and_filtered(
    client: AsyncClient, db: AsyncSession
) -> None:
    first = await create_group(db, name="БВТ2601", code="CODE-1")
    second = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_teacher(db, "teacher@example.com", "password-1", [first, second])
    ids = []
    for email, group, code in [
        ("s1@example.com", first, "CODE-1"),
        ("s2@example.com", first, "CODE-1"),
        ("s3@example.com", second, "CODE-2"),
    ]:
        await create_student(client, db, group, code, email)
        ids.append(await student_id(client))
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [first.id, second.id], term="autumn", year=2026)
    await assign_exam(client, course["id"], first, "graded_credit")
    url = f"/api/courses/{course['id']}/final-grades"
    await client.put(f"{url}/{ids[1]}", json={"grade": 4})

    page_one = (await client.get(url, params={"per_page": 2})).json()
    page_two = (await client.get(url, params={"per_page": 2, "page": 2})).json()
    by_group = (await client.get(url, params={"group_id": str(second.id)})).json()
    too_many = await client.get(url, params={"per_page": 101})

    assert (page_one["total"], page_one["pages"]) == (3, 2)
    assert [item["student_id"] for item in page_one["items"]] == ids[:2]
    assert [item["student_id"] for item in page_two["items"]] == ids[2:]
    assert [item["grade"] for item in page_one["items"]] == [None, 4]
    # У второй группы форма контроля ещё не назначена.
    assert [item["exam_type"] for item in page_one["items"] + page_two["items"]] == [
        "graded_credit",
        "graded_credit",
        None,
    ]
    assert [item["student_id"] for item in by_group["items"]] == [ids[2]]
    assert too_many.status_code == 422


@pytest.mark.case(id="UC-T17-004")
async def test_credit_is_passed_or_not_and_others_are_grades(
    client: AsyncClient, db: AsyncSession
) -> None:
    credit_group = await create_group(db, name="БВТ2601", code="CODE-1")
    graded_group = await create_group(db, name="БВТ2602", code="CODE-2")
    exam_group = await create_group(db, name="БВТ2603", code="CODE-3")
    bare_group = await create_group(db, name="БВТ2604", code="CODE-4")
    groups = [credit_group, graded_group, exam_group, bare_group]
    await create_teacher(db, "teacher@example.com", "password-1", groups)
    students = []
    for index, group in enumerate(groups, start=1):
        await create_student(client, db, group, f"CODE-{index}", f"s{index}@example.com")
        students.append(await student_id(client))
    await sign_in(client, "teacher@example.com", "password-1")
    course = await create_course(client, [group.id for group in groups], term="autumn", year=2026)
    await assign_exam(client, course["id"], credit_group, "credit")
    await assign_exam(client, course["id"], graded_group, "graded_credit")
    await assign_exam(client, course["id"], exam_group, "exam")
    url = f"/api/courses/{course['id']}/final-grades"

    passed = await client.put(f"{url}/{students[0]}", json={"passed": True})
    failed = await client.put(f"{url}/{students[0]}", json={"passed": False})
    credit_with_grade = await client.put(f"{url}/{students[0]}", json={"grade": 5})
    graded = await client.put(f"{url}/{students[1]}", json={"grade": 4})
    graded_with_passed = await client.put(f"{url}/{students[1]}", json={"passed": True})
    exam = await client.put(f"{url}/{students[2]}", json={"grade": 2})
    exam_with_passed = await client.put(f"{url}/{students[2]}", json={"passed": False})
    no_exam = await client.put(f"{url}/{students[3]}", json={"grade": 5})
    table = (await client.get(url)).json()["items"]
    await sign_in(client, "s1@example.com", "password-1")
    mine = (await client.get(f"{url}/me")).json()

    assert (passed.json()["passed"], passed.json()["grade"], passed.json()["exam_type"]) == (
        True,
        None,
        "credit",
    )
    assert failed.json()["passed"] is False
    for rejected in (credit_with_grade, graded_with_passed, exam_with_passed):
        assert (rejected.status_code, error_code(rejected)) == (
            422,
            "final_grades.result_kind_mismatch",
        )
    assert (graded.json()["grade"], graded.json()["passed"]) == (4, None)
    assert (exam.json()["grade"], exam.json()["passed"]) == (2, None)
    assert (no_exam.status_code, error_code(no_exam)) == (422, "final_grades.exam_not_assigned")
    assert [(row["exam_type"], row["grade"], row["passed"]) for row in table] == [
        ("credit", None, False),
        ("graded_credit", 4, None),
        ("exam", 2, None),
        (None, None, None),
    ]
    assert (mine["exam_type"], mine["grade"], mine["passed"]) == ("credit", None, False)


@pytest.mark.case(id="UC-S8-001")
async def test_student_sees_own_final_grade_and_exam(client: AsyncClient, db: AsyncSession) -> None:
    course, group = await autumn_course(client, db)
    other_group = await create_group(db, name="БВТ2602", code="CODE-2")
    await create_student(client, db, other_group, "CODE-2", "stranger@example.com")
    await sign_in(client, "student@example.com", "password-1")
    student = await student_id(client)
    url = f"/api/courses/{course['id']}/final-grades"

    pending = (await client.get(f"{url}/me")).json()
    await sign_in(client, "teacher@example.com", "password-1")
    await assign_exam(client, course["id"], group, "exam")
    await client.put(f"{url}/{student}", json={"grade": 4})
    teacher_me = await client.get(f"{url}/me")
    await sign_in(client, "student@example.com", "password-1")
    mine = (await client.get(f"{url}/me")).json()
    await sign_in(client, "stranger@example.com", "password-1")
    stranger = await client.get(f"{url}/me")

    assert pending == {"exam_type": None, "grade": None, "passed": None, "graded_at": None}
    assert (teacher_me.status_code, error_code(teacher_me)) == (403, "final_grades.student_only")
    assert (mine["exam_type"], mine["grade"], mine["passed"]) == ("exam", 4, None)
    assert mine["graded_at"] is not None
    assert (stranger.status_code, error_code(stranger)) == (403, "final_grades.course_forbidden")
