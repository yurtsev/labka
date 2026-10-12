from src.api.exams.dto import ExamFields
from src.api.exams.schemas import ExamRequest


def exam_fields(body: ExamRequest) -> ExamFields:
    """Поля экзамена из запроса; пустая аудитория — `None`."""
    return ExamFields(
        group_id=body.group_id,
        exam_type=body.exam_type,
        day=body.day,
        slot=body.slot,
        room=body.room or None,
    )
