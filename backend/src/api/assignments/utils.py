from src.api.assignments.dto import AssignmentFields
from src.api.assignments.schemas import (
    AssignmentUpdateRequest,
    RangeScaleSchema,
)
from src.core.grading.dto import Scale


def assignment_fields(body: AssignmentUpdateRequest) -> AssignmentFields:
    """Поля задания из запроса; пустые описание и пояснение к оценке — `None`."""
    scale = body.scale
    return AssignmentFields(
        type=body.type,
        title=body.title,
        description=body.description or None,
        deadline_type=body.deadline_type,
        deadline_at=body.deadline_at,
        scale=Scale(
            type=scale.type,
            min=scale.min if isinstance(scale, RangeScaleSchema) else None,
            max=scale.max if isinstance(scale, RangeScaleSchema) else None,
        )
        if scale is not None
        else None,
        grading_note=body.grading_note or None,
    )
