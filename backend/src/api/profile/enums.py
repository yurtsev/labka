from enum import StrEnum


class AvatarContentType(StrEnum):
    """Типы картинок, которые можно поставить аватаркой. SVG нет: в нём может быть скрипт."""

    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"
    GIF = "image/gif"
