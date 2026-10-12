from src.core.errors import NotFoundError


class NotificationNotFoundError(NotFoundError):
    code = "notifications.not_found"
    message = "Уведомление не найдено"
