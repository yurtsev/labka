from src.api.materials.dto import MaterialFields
from src.api.materials.schemas import MaterialUpdateRequest


def material_fields(body: MaterialUpdateRequest) -> MaterialFields:
    """Поля материала из запроса; пустой текст — `None`."""
    return MaterialFields(title=body.title, text=body.text or None)
