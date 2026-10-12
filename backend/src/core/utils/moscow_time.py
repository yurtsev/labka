from datetime import datetime
from zoneinfo import ZoneInfo


def assume_moscow(moment: datetime) -> datetime:
    """Момент без часового пояса считается московским; с поясом — остаётся как есть."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=ZoneInfo("Europe/Moscow"))
    return moment


def to_moscow(moment: datetime) -> datetime:
    """Тот же момент в московском времени — для вывода дедлайнов."""
    return moment.astimezone(ZoneInfo("Europe/Moscow"))
