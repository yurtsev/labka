from src.core.errors import ConflictError, NotFoundError


class DirectionNotFoundError(NotFoundError):
    code = "admin.direction_not_found"
    message = "Направление не найдено"


class GroupNotFoundError(NotFoundError):
    code = "admin.group_not_found"
    message = "Группа не найдена"


class GroupNameTakenError(ConflictError):
    code = "admin.group_name_taken"
    message = "Группа с таким названием уже есть"


class InviteNotFoundError(NotFoundError):
    code = "admin.invite_not_found"
    message = "Почта не найдена в списках групп"


class InviteEmailTakenError(ConflictError):
    code = "admin.invite_email_taken"
    message = "Эта почта уже есть в списке одной из групп"
