from src.api.courses.dto import CourseFields, Scale, SemesterChoice
from src.api.courses.schemas import CourseCreateRequest, CourseUpdateRequest, RangeScaleSchema


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


def semester_choice(body: CourseCreateRequest) -> SemesterChoice | None:
    """Семестр из запроса; `None` — не задан, будет текущий."""
    if body.term is None or body.year is None:
        return None
    return SemesterChoice(term=body.term, year=body.year)
