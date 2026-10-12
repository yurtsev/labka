from datetime import date, datetime, time

from src.core.db.enums import ExamType, NotificationType, ReviewVerdict
from src.core.errors import InternalError
from src.core.notifications.dto import Payload, Rendered, Target
from src.core.notifications.enums import NotificationSection
from src.core.utils.moscow_time import to_moscow


class NotificationRenderer:
    """Заголовок, текст и переход для уведомления по его типу и слепку данных."""

    @staticmethod
    def render(type: NotificationType, payload: Payload) -> Rendered:
        """Собирает уведомление.

        Raises:
            InternalError: в слепке нет поля, без которого этот тип не собрать.
        """
        course = NotificationRenderer._need(payload.course_name, type, "course_name")
        course_id = payload.course_id
        match type:
            case NotificationType.COURSE_ADDED:
                return Rendered(
                    "Вас добавили в курс",
                    f"«{course}»",
                    Target(NotificationSection.COURSE_FEED, course_id),
                )
            case NotificationType.ASSIGNMENT_CREATED | NotificationType.ASSIGNMENT_UPDATED:
                title = (
                    "Новое задание"
                    if type == NotificationType.ASSIGNMENT_CREATED
                    else "Задание изменено"
                )
                return Rendered(
                    title,
                    f"«{NotificationRenderer._assignment(payload, type)}» в курсе «{course}»",
                    NotificationRenderer._assignment_target(payload),
                )
            case NotificationType.MATERIAL_ADDED:
                material = NotificationRenderer._need(
                    payload.material_title, type, "material_title"
                )
                return Rendered(
                    "Новый материал",
                    f"«{material}» в курсе «{course}»",
                    Target(NotificationSection.MATERIALS, course_id),
                )
            case NotificationType.ANNOUNCEMENT_CREATED:
                return Rendered(
                    "Новое объявление",
                    f"Курс «{course}»",
                    Target(NotificationSection.COURSE_FEED, course_id),
                )
            case NotificationType.SCHEDULE_CHANGED:
                return Rendered(
                    "Расписание изменено",
                    f"Курс «{course}»",
                    Target(NotificationSection.SCHEDULE, course_id),
                )
            case NotificationType.SUBMISSION_REVIEWED:
                accepted = payload.verdict == ReviewVerdict.ACCEPTED
                return Rendered(
                    "Работа принята" if accepted else "Работа возвращена на доработку",
                    f"«{NotificationRenderer._assignment(payload, type)}» в курсе «{course}»",
                    NotificationRenderer._assignment_target(payload),
                )
            case NotificationType.GRADE_CHANGED:
                return Rendered(
                    "Оценка исправлена",
                    f"«{NotificationRenderer._assignment(payload, type)}» в курсе «{course}»",
                    NotificationRenderer._assignment_target(payload),
                )
            case NotificationType.DEADLINE_REMINDER:
                deadline = NotificationRenderer._need(payload.deadline_at, type, "deadline_at")
                return Rendered(
                    "Скоро дедлайн",
                    f"«{NotificationRenderer._assignment(payload, type)}» — до "
                    f"{NotificationRenderer._moment(deadline)}",
                    NotificationRenderer._assignment_target(payload),
                )
            case NotificationType.SUBMISSION_CREATED:
                student = NotificationRenderer._need(payload.student_name, type, "student_name")
                return Rendered(
                    "Новая работа на проверку",
                    f"{student} — «{NotificationRenderer._assignment(payload, type)}», "
                    f"попытка №{payload.attempt} · «{course}»",
                    Target(
                        NotificationSection.REVIEW,
                        course_id,
                        payload.assignment_id,
                        payload.submission_id,
                        payload.student_id,
                    ),
                )
            case NotificationType.EXAM_ASSIGNED | NotificationType.EXAM_CHANGED:
                return NotificationRenderer._exam(type, payload, course)
            case NotificationType.FINAL_RESULT_SET:
                return Rendered(
                    "Итоговый результат выставлен",
                    f"«{course}»: {NotificationRenderer._result(payload)}",
                    Target(NotificationSection.FINAL_RESULT, course_id),
                )

    @staticmethod
    def _exam(type: NotificationType, payload: Payload, course: str) -> Rendered:
        form = NotificationRenderer._form(payload.exam_type)
        day = NotificationRenderer._need(payload.day, type, "day")
        if type == NotificationType.EXAM_ASSIGNED:
            title = f"Назначен {form}"
        elif payload.removed:
            title = f"{form.capitalize()} отменён"
        else:
            title = f"{form.capitalize()} изменён"
        when = NotificationRenderer._day(day, payload.starts_at)
        text = f"«{course}»" if payload.removed else f"«{course}»: {when}"
        return Rendered(
            title, text, Target(NotificationSection.CALENDAR, payload.course_id, day=day)
        )

    @staticmethod
    def _form(exam_type: ExamType | None) -> str:
        match exam_type:
            case ExamType.CREDIT:
                return "зачёт"
            case ExamType.GRADED_CREDIT:
                return "дифф. зачёт"
            case _:
                return "экзамен"

    @staticmethod
    def _result(payload: Payload) -> str:
        if payload.passed is not None:
            return "зачтено" if payload.passed else "не зачтено"
        match payload.grade:
            case 5:
                return "5 (отлично)"
            case 4:
                return "4 (хорошо)"
            case 3:
                return "3 (удовлетворительно)"
            case 2:
                return "2 (не сдал)"
            case _:
                raise InternalError({"field": "grade"})

    @staticmethod
    def _assignment(payload: Payload, type: NotificationType) -> str:
        return NotificationRenderer._need(payload.assignment_title, type, "assignment_title")

    @staticmethod
    def _assignment_target(payload: Payload) -> Target:
        return Target(NotificationSection.ASSIGNMENT, payload.course_id, payload.assignment_id)

    @staticmethod
    def _need[T](value: T | None, type: NotificationType, field: str) -> T:
        if value is None:
            raise InternalError({"notification_type": type.value, "field": field})
        return value

    @staticmethod
    def _month(day: date) -> str:
        months = (
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        )
        return f"{day.day} {months[day.month - 1]}"

    @staticmethod
    def _day(day: date, starts_at: time | None) -> str:
        if starts_at is None:
            return NotificationRenderer._month(day)
        return f"{NotificationRenderer._month(day)} в {starts_at:%H:%M}"

    @staticmethod
    def _moment(moment: datetime) -> str:
        local = to_moscow(moment)
        return f"{NotificationRenderer._month(local.date())}, {local:%H:%M} (МСК)"
