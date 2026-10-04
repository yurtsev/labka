from src.api.courses.dto import CourseFields, Scale
from src.api.courses.schemas import CourseUpdateRequest, RangeScaleSchema


def course_fields(body: CourseUpdateRequest) -> CourseFields:
    """Поля курса из запроса; пустые описание и пояснение к оценке — `None`."""
    scale = body.scale
    return CourseFields(
        name=body.name,
        description=body.description or None,
        scale=Scale(
            type=scale.type,
            min=scale.min if isinstance(scale, RangeScaleSchema) else None,
            max=scale.max if isinstance(scale, RangeScaleSchema) else None,
        ),
        grading_note=body.grading_note or None,
    )
