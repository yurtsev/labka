from dataclasses import dataclass


@dataclass(frozen=True)
class PresignedUpload:
    """Форма загрузки для браузера: POST multipart на `url` с `fields` и файлом последним."""

    key: str
    url: str
    fields: dict[str, str]


@dataclass(frozen=True)
class StoredObject:
    size: int
    content_type: str
