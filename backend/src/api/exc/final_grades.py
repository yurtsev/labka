from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "final_grades.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "final_grades.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "final_grades.course_archived"
    message = "Курс в архиве: изменения недоступны"


class StudentOnlyError(ForbiddenError):
    code = "final_grades.student_only"
    message = "Своя итоговая оценка доступна только студенту"


class StudentNotInCourseError(NotFoundError):
    code = "final_grades.student_not_in_course"
    message = "Студента нет в группах курса"


class FinalGradeNotFoundError(NotFoundError):
    code = "final_grades.not_found"
    message = "Итоговая оценка не выставлена"


class ExamNotAssignedError(RuleViolationError):
    code = "final_grades.exam_not_assigned"
    message = "Сначала назначьте группе зачёт, дифф. зачёт или экзамен"


class ResultKindMismatchError(RuleViolationError):
    code = "final_grades.result_kind_mismatch"
    message = (
        "Для зачёта ставится «зачтено» или «не зачтено», для дифф. зачёта и экзамена — оценка 2–5"
    )
