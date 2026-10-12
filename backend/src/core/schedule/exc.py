from src.core.errors import CoreError


class SlotNotFoundError(CoreError):
    code = "schedule.slot_not_found"
    message = "Такого окна пары нет в сетке"
