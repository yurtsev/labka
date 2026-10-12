from src.api.schedule.dto import ExtraFields, RuleFields
from src.api.schedule.schemas import ExtraRequest, RuleRequest


def rule_fields(body: RuleRequest) -> RuleFields:
    """Поля правила из запроса; пустая аудитория — `None`."""
    return RuleFields(
        group_id=body.group_id,
        lesson_type=body.lesson_type,
        weekday=body.weekday,
        slot=body.slot,
        repeat=body.repeat,
        room=body.room or None,
    )


def extra_fields(body: ExtraRequest) -> ExtraFields:
    """Поля разового занятия из запроса; пустая аудитория — `None`."""
    return ExtraFields(
        group_id=body.group_id,
        lesson_type=body.lesson_type,
        day=body.day,
        slot=body.slot,
        room=body.room or None,
    )
