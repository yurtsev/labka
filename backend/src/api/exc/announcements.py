from src.core.errors import ConflictError, ForbiddenError, NotFoundError


class CourseNotFoundError(NotFoundError):
    code = "announcements.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "announcements.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "announcements.course_archived"
    message = "Курс в архиве: изменения недоступны"


class AnnouncementNotFoundError(NotFoundError):
    code = "announcements.not_found"
    message = "Объявление не найдено"
