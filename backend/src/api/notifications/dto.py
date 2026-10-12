from dataclasses import dataclass


@dataclass(frozen=True)
class ReadAll:
    """Сколько уведомлений отмечено прочитанными и сколько осталось непрочитанных."""

    marked: int
    unread_count: int
