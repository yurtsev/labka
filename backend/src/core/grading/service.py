from datetime import datetime

from src.core.db.dto.progress import ProgressRow, SummaryRow
from src.core.db.enums import DeadlineType, ReviewVerdict, ScaleType
from src.core.db.models.assignment import Assignment
from src.core.db.models.course import Course
from src.core.grading.dto import Grade, Progress, Scale, Summary
from src.core.grading.enums import ProgressStatus, SubmitWindow
from src.core.grading.exc import GradeOutOfScaleError, GradeRequiredError


class GradingService:
    """Шкалы, статусы и оценки по заданиям. Без I/O: статусы считает БД, здесь — их смысл."""

    @staticmethod
    def effective_scale(assignment: Assignment, course: Course) -> Scale:
        """Шкала задания: своя или, если её нет, шкала курса."""
        if assignment.scale_type is not None:
            return Scale(assignment.scale_type, assignment.scale_min, assignment.scale_max)
        return Scale(course.scale_type, course.scale_min, course.scale_max)

    @staticmethod
    def progress(row: ProgressRow | None, assignment: Assignment, now: datetime) -> Progress:
        """Положение студента по заданию на момент `now`; `row=None` — попыток нет."""
        can_submit = GradingService.submit_window(assignment, row, now) in (
            SubmitWindow.OPEN,
            SubmitWindow.LATE,
        )
        if row is None:
            return Progress(ProgressStatus.NOT_SUBMITTED, None, 0, None, False, can_submit)
        grade = Grade(row.grade_score, row.grade_passed)
        return Progress(
            status=row.status,
            grade=grade if grade.is_set else None,
            attempts=row.attempts,
            last_submitted_at=row.last_submitted_at,
            last_is_late=row.last_is_late,
            can_submit=can_submit,
        )

    @staticmethod
    def submit_window(
        assignment: Assignment, row: ProgressRow | None, now: datetime
    ) -> SubmitWindow:
        """Можно ли сейчас отправить попытку — единое правило для отправки и для карточки задания.

        После жёсткого дедлайна пересдача разрешена, только если студент сдавал до срока, а
        последнюю попытку вернули на доработку.
        """
        if row is not None and row.status == ProgressStatus.ACCEPTED:
            return SubmitWindow.ACCEPTED
        deadline = assignment.deadline_at
        if deadline is None or now <= deadline:
            return SubmitWindow.OPEN
        if assignment.deadline_type != DeadlineType.HARD:
            return SubmitWindow.LATE
        if (
            row is not None
            and row.status == ProgressStatus.REVISION
            and row.first_submitted_at is not None
            and row.first_submitted_at <= deadline
        ):
            return SubmitWindow.OPEN
        return SubmitWindow.CLOSED

    @staticmethod
    def summary(students: int, row: SummaryRow | None) -> Summary:
        """Сводка по заданию среди студентов курса; `None` — никто не сдавал."""
        if row is None:
            return Summary(students=students, submitted=0, on_review=0, accepted=0)
        return Summary(
            students=students,
            submitted=row.submitted,
            on_review=row.on_review,
            accepted=row.accepted,
        )

    @staticmethod
    def check_grade(scale: Scale, verdict: ReviewVerdict, grade: Grade) -> None:
        """Проверяет оценку по шкале и вердикту.

        Raises:
            GradeRequiredError: вердикт «принято», а оценки нет.
            GradeOutOfScaleError: оценка другого вида или вне диапазона шкалы.
        """
        if not grade.is_set:
            if verdict == ReviewVerdict.ACCEPTED:
                raise GradeRequiredError
            return
        match scale.type:
            case ScaleType.RANGE:
                if (
                    grade.passed is not None
                    or grade.score is None
                    or scale.min is None
                    or scale.max is None
                    or not scale.min <= grade.score <= scale.max
                ):
                    raise GradeOutOfScaleError({"min": scale.min, "max": scale.max})
            case ScaleType.BINARY:
                if grade.score is not None:
                    raise GradeOutOfScaleError({"scale": scale.type.value})
