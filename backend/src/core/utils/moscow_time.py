from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def assume_moscow(moment: datetime) -> datetime:
    """Момент без часового пояса считается московским; с поясом — остаётся как есть."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=ZoneInfo("Europe/Moscow"))
    return moment


def to_moscow(moment: datetime) -> datetime:
    """Тот же момент в московском времени — для вывода дедлайнов."""
    return moment.astimezone(ZoneInfo("Europe/Moscow"))


def now_moscow() -> datetime:
    """Текущий момент в московском времени."""
    return datetime.now(ZoneInfo("Europe/Moscow"))


def start_of_day_moscow(day: date) -> datetime:
    """Начало дня по Москве — полночь, с часовым поясом."""
    return datetime.combine(day, time.min, tzinfo=ZoneInfo("Europe/Moscow"))
