from src.core.errors import ForbiddenError, NotFoundError


class CourseNotFoundError(NotFoundError):
    code = "feed.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "feed.course_forbidden"
    message = "Нет доступа к курсу"
