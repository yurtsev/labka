from src.api.submissions.dto import UploadedFile
from src.api.submissions.schemas import UploadedFileRequest


def uploaded_file(body: UploadedFileRequest) -> UploadedFile:
    return UploadedFile(key=body.key, file_name=body.file_name)
