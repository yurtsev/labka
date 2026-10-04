from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class MaterialFields:
    """Редактируемые поля материала."""

    title: str
    text: str | None


@dataclass(frozen=True)
class UploadedFile:
    """Файл, который браузер уже загрузил в S3 по форме бэкенда."""

    key: str
    file_name: str


@dataclass(frozen=True)
class MaterialFile:
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


@dataclass(frozen=True)
class Material:
    id: UUID
    title: str
    text: str | None
    created_at: datetime
    updated_at: datetime
    files: tuple[MaterialFile, ...]
