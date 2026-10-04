from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "courses.not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "courses.forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "courses.archived"
    message = "Курс в архиве: изменения недоступны"


class TeacherOnlyError(ForbiddenError):
    code = "courses.teacher_only"
    message = "Действие доступно только преподавателю"


class GroupNotAvailableError(RuleViolationError):
    code = "courses.group_not_available"
    message = "Группа не прикреплена к вам или неактивна"


class GroupAlreadyInCourseError(ConflictError):
    code = "courses.group_already_in_course"
    message = "Группа уже есть в курсе"


class GroupNotInCourseError(NotFoundError):
    code = "courses.group_not_in_course"
    message = "Этой группы нет в курсе"
