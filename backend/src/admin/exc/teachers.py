from src.core.errors import ConflictError, NotFoundError, RuleViolationError


class TeacherNotFoundError(NotFoundError):
    code = "admin.teacher_not_found"
    message = "Преподаватель не найден"


class DepartmentNotFoundError(NotFoundError):
    code = "admin.department_not_found"
    message = "Кафедра не найдена"


class TeacherGroupNotFoundError(NotFoundError):
    code = "admin.teacher_group_not_found"
    message = "Одна из выбранных групп не найдена"


class TeacherEmailTakenError(ConflictError):
    code = "admin.teacher_email_taken"
    message = "Пользователь с этой почтой уже есть"


class TeacherGroupInactiveError(RuleViolationError):
    code = "admin.teacher_group_inactive"
    message = "Нельзя прикрепить неактивную группу"
