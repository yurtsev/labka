from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "reviews.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "reviews.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "reviews.course_archived"
    message = "Курс в архиве: проверка недоступна"


class TeacherOnlyError(ForbiddenError):
    code = "reviews.teacher_only"
    message = "Проверка доступна только преподавателю"


class AssignmentNotFoundError(NotFoundError):
    code = "reviews.assignment_not_found"
    message = "Задание не найдено"


class StudentNotFoundError(NotFoundError):
    code = "reviews.student_not_found"
    message = "Студент не найден"


class SubmissionNotFoundError(NotFoundError):
    code = "reviews.submission_not_found"
    message = "Попытка не найдена"


class AlreadyReviewedError(ConflictError):
    code = "reviews.already_reviewed"
    message = "Попытка уже проверена — оценку можно исправить"


class NotLatestSubmissionError(ConflictError):
    code = "reviews.not_latest"
    message = "Студент отправил более новую попытку — проверьте её"


class NotReviewedError(ConflictError):
    code = "reviews.not_reviewed"
    message = "Попытка ещё не проверена"


class GradeRequiredError(RuleViolationError):
    code = "reviews.grade_required"
    message = "При вердикте «принято» оценка обязательна"


class GradeOutOfScaleError(RuleViolationError):
    code = "reviews.grade_out_of_scale"
    message = "Оценка не соответствует шкале задания"
