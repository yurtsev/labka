from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "submissions.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "submissions.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "submissions.course_archived"
    message = "Курс в архиве: сдавать работы нельзя"


class AssignmentNotFoundError(NotFoundError):
    code = "submissions.assignment_not_found"
    message = "Задание не найдено"


class StudentOnlyError(ForbiddenError):
    code = "submissions.student_only"
    message = "Сдавать работы может только студент"


class EmptySubmissionError(RuleViolationError):
    code = "submissions.empty"
    message = "Добавьте файл или комментарий"


class AlreadyAcceptedError(ConflictError):
    code = "submissions.already_accepted"
    message = "Работа уже принята"


class DeadlinePassedError(ConflictError):
    code = "submissions.deadline_passed"
    message = "Срок сдачи истёк"


class ConcurrentSubmissionError(ConflictError):
    code = "submissions.concurrent"
    message = "Попытка уже отправлена из другой вкладки — обновите страницу"


class FileTooLargeError(RuleViolationError):
    code = "submissions.file_too_large"
    message = "Файл больше допустимого размера"


class FileNotUploadedError(RuleViolationError):
    code = "submissions.file_not_uploaded"
    message = "Файл не загружен в хранилище"


class ForeignFileKeyError(RuleViolationError):
    code = "submissions.foreign_file_key"
    message = "Файл загружен не для этой сдачи"


class FileAlreadyAttachedError(ConflictError):
    code = "submissions.file_already_attached"
    message = "Этот файл уже прикреплён к попытке"
