from src.core.errors import ConflictError, RuleViolationError, UnauthenticatedError


class InvalidGroupCodeError(RuleViolationError):
    code = "auth.invalid_group_code"
    message = "Неверный код группы"


class EmailNotInvitedError(RuleViolationError):
    code = "auth.email_not_invited"
    message = "Этой почты нет в списке группы"


class EmailAlreadyRegisteredError(ConflictError):
    code = "auth.email_already_registered"
    message = "Аккаунт с этой почтой уже зарегистрирован"


class InvalidCredentialsError(UnauthenticatedError):
    code = "auth.invalid_credentials"
    message = "Неверный email или пароль"


class AccountDeactivatedError(UnauthenticatedError):
    code = "auth.account_deactivated"
    message = "Аккаунт деактивирован"


class InvalidRefreshTokenError(UnauthenticatedError):
    code = "auth.invalid_refresh_token"
    message = "Сессия недействительна, войдите заново"


class RefreshTokenReusedError(UnauthenticatedError):
    code = "auth.refresh_token_reused"
    message = "Сессия отозвана, войдите заново"


class WrongCurrentPasswordError(RuleViolationError):
    code = "auth.wrong_current_password"
    message = "Неверный текущий пароль"
