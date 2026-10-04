from src.core.errors import CoreError


class CourseNotFoundError(CoreError):
    code = "access.course_not_found"
    message = "Курс не найден"


class CourseAccessDeniedError(CoreError):
    code = "access.course_access_denied"
    message = "Нет доступа к курсу"


class CourseArchivedError(CoreError):
    code = "access.course_archived"
    message = "Курс в архиве"


class GroupNotAttachedError(CoreError):
    code = "access.group_not_attached"
    message = "Группа не прикреплена к преподавателю или неактивна"
