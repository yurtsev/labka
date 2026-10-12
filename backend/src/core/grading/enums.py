from enum import StrEnum


class ProgressStatus(StrEnum):
    """Статус задания для студента: не сдано → на проверке → на доработку → … → принято."""

    NOT_SUBMITTED = "not_submitted"
    ON_REVIEW = "on_review"
    REVISION = "revision"
    ACCEPTED = "accepted"
