from src.core.errors import RuleViolationError


class AvatarNotImageError(RuleViolationError):
    code = "profile.avatar_not_image"
    message = "Аватарка должна быть картинкой PNG, JPEG, WebP или GIF"


class AvatarTooLargeError(RuleViolationError):
    code = "profile.avatar_too_large"
    message = "Файл больше допустимого размера"


class AvatarNotUploadedError(RuleViolationError):
    code = "profile.avatar_not_uploaded"
    message = "Файл не загружен в хранилище"


class ForeignAvatarKeyError(RuleViolationError):
    code = "profile.foreign_avatar_key"
    message = "Файл загружен не для вашей аватарки"
