from src.core.errors import ForbiddenError, NotFoundError, RuleViolationError


class StudentOnlyError(ForbiddenError):
    code = "personal_tasks.student_only"
    message = "Личные задачи доступны только студенту"


class TaskNotFoundError(NotFoundError):
    code = "personal_tasks.not_found"
    message = "Задача не найдена"


class InvalidRangeError(RuleViolationError):
    code = "personal_tasks.invalid_range"
    message = "Начало периода позже конца или период слишком длинный"
