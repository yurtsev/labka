from src.core.errors import NotFoundError, RuleViolationError


class UsersNotFoundError(NotFoundError):
    code = "admin.users_not_found"
    message = "Выбранных пользователей нет"


class TargetGroupNotFoundError(NotFoundError):
    code = "admin.target_group_not_found"
    message = "Группа не найдена"


class TargetGroupInactiveError(RuleViolationError):
    code = "admin.target_group_inactive"
    message = "Нельзя перевести студентов в неактивную группу"
