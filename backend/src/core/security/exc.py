from src.core.errors import CoreError, UnauthenticatedError


class NotAuthenticatedError(UnauthenticatedError):
    code = "security.not_authenticated"
    message = "Требуется вход в систему"


class MalformedRefreshTokenError(CoreError):
    code = "security.malformed_refresh_token"
    message = "Некорректный refresh-токен"
