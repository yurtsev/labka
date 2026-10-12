from datetime import UTC, date, datetime, time
from uuid import uuid7

import pytest

from src.core.db.enums import ExamType, NotificationType, ReviewVerdict
from src.core.errors import InternalError
from src.core.notifications.dto import Payload
from src.core.notifications.enums import NotificationSection
from src.core.notifications.renderer import NotificationRenderer

COURSE = uuid7()
ASSIGNMENT = uuid7()
SUBMISSION = uuid7()
STUDENT = uuid7()


def payload(**fields: object) -> Payload:
    base: dict[str, object] = {"course_id": COURSE, "course_name": "Алгоритмы"}
    return Payload.model_validate({**base, **fields})


def assignment_payload(**fields: object) -> Payload:
    return payload(assignment_id=ASSIGNMENT, assignment_title="Лаба 1", **fields)


@pytest.mark.case(id="NOTIF-RENDER-001")
@pytest.mark.parametrize(
    ("type", "data", "title", "text", "section"),
    [
        (
            NotificationType.COURSE_ADDED,
            payload(),
            "Вас добавили в курс",
            "«Алгоритмы»",
            NotificationSection.COURSE_FEED,
        ),
        (
            NotificationType.ASSIGNMENT_CREATED,
            assignment_payload(),
            "Новое задание",
            "«Лаба 1» в курсе «Алгоритмы»",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.ASSIGNMENT_UPDATED,
            assignment_payload(),
            "Задание изменено",
            "«Лаба 1» в курсе «Алгоритмы»",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.MATERIAL_ADDED,
            payload(material_title="Учебник"),
            "Новый материал",
            "«Учебник» в курсе «Алгоритмы»",
            NotificationSection.MATERIALS,
        ),
        (
            NotificationType.ANNOUNCEMENT_CREATED,
            payload(),
            "Новое объявление",
            "Курс «Алгоритмы»",
            NotificationSection.COURSE_FEED,
        ),
        (
            NotificationType.SCHEDULE_CHANGED,
            payload(),
            "Расписание изменено",
            "Курс «Алгоритмы»",
            NotificationSection.SCHEDULE,
        ),
        (
            NotificationType.SUBMISSION_REVIEWED,
            assignment_payload(verdict=ReviewVerdict.ACCEPTED),
            "Работа принята",
            "«Лаба 1» в курсе «Алгоритмы»",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.SUBMISSION_REVIEWED,
            assignment_payload(verdict=ReviewVerdict.REVISION),
            "Работа возвращена на доработку",
            "«Лаба 1» в курсе «Алгоритмы»",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.GRADE_CHANGED,
            assignment_payload(),
            "Оценка исправлена",
            "«Лаба 1» в курсе «Алгоритмы»",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.DEADLINE_REMINDER,
            assignment_payload(deadline_at=datetime(2026, 9, 3, 15, 0, tzinfo=UTC)),
            "Скоро дедлайн",
            "«Лаба 1» — до 3 сентября, 18:00 (МСК)",
            NotificationSection.ASSIGNMENT,
        ),
        (
            NotificationType.SUBMISSION_CREATED,
            assignment_payload(
                student_id=STUDENT,
                student_name="Иванов Иван",
                submission_id=SUBMISSION,
                attempt=2,
            ),
            "Новая работа на проверку",
            "Иванов Иван — «Лаба 1», попытка №2 · «Алгоритмы»",
            NotificationSection.REVIEW,
        ),
        (
            NotificationType.EXAM_ASSIGNED,
            payload(exam_type=ExamType.EXAM, day=date(2027, 1, 12), starts_at=time(11, 15)),
            "Назначен экзамен",
            "«Алгоритмы»: 12 января в 11:15",
            NotificationSection.CALENDAR,
        ),
        (
            NotificationType.EXAM_ASSIGNED,
            payload(exam_type=ExamType.CREDIT, day=date(2026, 12, 28), starts_at=time(9, 30)),
            "Назначен зачёт",
            "«Алгоритмы»: 28 декабря в 09:30",
            NotificationSection.CALENDAR,
        ),
        (
            NotificationType.EXAM_CHANGED,
            payload(exam_type=ExamType.GRADED_CREDIT, day=date(2027, 1, 20), starts_at=time(13, 0)),
            "Дифф. зачёт изменён",
            "«Алгоритмы»: 20 января в 13:00",
            NotificationSection.CALENDAR,
        ),
        (
            NotificationType.EXAM_CHANGED,
            payload(exam_type=ExamType.EXAM, day=date(2027, 1, 12), removed=True),
            "Экзамен отменён",
            "«Алгоритмы»",
            NotificationSection.CALENDAR,
        ),
        (
            NotificationType.FINAL_RESULT_SET,
            payload(grade=4),
            "Итоговый результат выставлен",
            "«Алгоритмы»: 4 (хорошо)",
            NotificationSection.FINAL_RESULT,
        ),
        (
            NotificationType.FINAL_RESULT_SET,
            payload(passed=False),
            "Итоговый результат выставлен",
            "«Алгоритмы»: не зачтено",
            NotificationSection.FINAL_RESULT,
        ),
    ],
)
def test_title_text_and_section(
    type: NotificationType, data: Payload, title: str, text: str, section: NotificationSection
) -> None:
    rendered = NotificationRenderer.render(type, data)

    assert (rendered.title, rendered.text, rendered.target.section) == (title, text, section)
    assert rendered.target.course_id == COURSE


@pytest.mark.case(id="NOTIF-RENDER-002")
def test_target_carries_ids_for_a_quick_jump() -> None:
    review = NotificationRenderer.render(
        NotificationType.SUBMISSION_CREATED,
        assignment_payload(
            student_id=STUDENT, student_name="Иванов Иван", submission_id=SUBMISSION, attempt=1
        ),
    ).target
    exam = NotificationRenderer.render(
        NotificationType.EXAM_ASSIGNED,
        payload(exam_type=ExamType.EXAM, day=date(2027, 1, 12), starts_at=time(11, 15)),
    ).target
    assignment = NotificationRenderer.render(
        NotificationType.ASSIGNMENT_CREATED, assignment_payload()
    ).target

    assert (review.assignment_id, review.submission_id, review.student_id) == (
        ASSIGNMENT,
        SUBMISSION,
        STUDENT,
    )
    assert exam.day == date(2027, 1, 12)
    assert assignment.assignment_id == ASSIGNMENT
    assert assignment.day is None


@pytest.mark.case(id="NOTIF-RENDER-003")
def test_payload_missing_a_required_field_is_an_internal_error() -> None:
    with pytest.raises(InternalError):
        NotificationRenderer.render(NotificationType.ASSIGNMENT_CREATED, payload())
    with pytest.raises(InternalError):
        NotificationRenderer.render(NotificationType.COURSE_ADDED, Payload())
