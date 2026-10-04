from src.api.materials.dto import MaterialFields, UploadedFile
from src.api.materials.schemas import MaterialUpdateRequest, UploadedFileRequest


def material_fields(body: MaterialUpdateRequest) -> MaterialFields:
    """Поля материала из запроса; пустой текст — `None`."""
    return MaterialFields(title=body.title, text=body.text or None)


def uploaded_file(body: UploadedFileRequest) -> UploadedFile:
    return UploadedFile(key=body.key, file_name=body.file_name)
