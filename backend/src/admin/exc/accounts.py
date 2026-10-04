from src.core.errors import ConflictError


class AdminEmailTakenError(ConflictError):
    code = "admin.admin_email_taken"
    message = "Пользователь с этой почтой уже есть"
