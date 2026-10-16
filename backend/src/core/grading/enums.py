from enum import StrEnum


class ProgressStatus(StrEnum):
    """Статус задания для студента: не сдано → на проверке → на доработку → … → принято."""

    NOT_SUBMITTED = "not_submitted"
    ON_REVIEW = "on_review"
    REVISION = "revision"
    ACCEPTED = "accepted"


class SubmitWindow(StrEnum):
    """Можно ли студенту сейчас отправить попытку по заданию."""

    OPEN = "open"
    # Мягкий дедлайн прошёл: попытку примут с пометкой «просрочено».
    LATE = "late"
    # Жёсткий дедлайн прошёл, а пересдача не разрешена.
    CLOSED = "closed"
    ACCEPTED = "accepted"
