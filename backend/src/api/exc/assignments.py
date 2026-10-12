from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "assignments.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "assignments.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "assignments.course_archived"
    message = "Курс в архиве: изменения недоступны"


class AssignmentNotFoundError(NotFoundError):
    code = "assignments.not_found"
    message = "Задание не найдено"


class AssignmentFileNotFoundError(NotFoundError):
    code = "assignments.file_not_found"
    message = "Файл не найден в задании"


class ScaleLockedError(ConflictError):
    code = "assignments.scale_locked"
    message = "Шкалу нельзя изменить: по заданию уже есть попытки"


class FileTooLargeError(RuleViolationError):
    code = "assignments.file_too_large"
    message = "Файл больше допустимого размера"


class FileNotUploadedError(RuleViolationError):
    code = "assignments.file_not_uploaded"
    message = "Файл не загружен в хранилище"


class ForeignFileKeyError(RuleViolationError):
    code = "assignments.foreign_file_key"
    message = "Файл загружен не для заданий этого курса"


class FileAlreadyAttachedError(ConflictError):
    code = "assignments.file_already_attached"
    message = "Этот файл уже прикреплён к заданию"


class TeacherOnlyError(ForbiddenError):
    code = "assignments.teacher_only"
    message = "Действие доступно только преподавателю"
