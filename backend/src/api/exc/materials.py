from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "materials.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "materials.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "materials.course_archived"
    message = "Курс в архиве: изменения недоступны"


class MaterialNotFoundError(NotFoundError):
    code = "materials.not_found"
    message = "Материал не найден"


class FileTooLargeError(RuleViolationError):
    code = "materials.file_too_large"
    message = "Файл больше допустимого размера"


class FileNotUploadedError(RuleViolationError):
    code = "materials.file_not_uploaded"
    message = "Файл не загружен в хранилище"


class ForeignFileKeyError(RuleViolationError):
    code = "materials.foreign_file_key"
    message = "Файл загружен не для материалов этого курса"


class MaterialFileNotFoundError(NotFoundError):
    code = "materials.file_not_found"
    message = "Файл не найден в материале"


class FileAlreadyAttachedError(ConflictError):
    code = "materials.file_already_attached"
    message = "Этот файл уже прикреплён к материалу"
