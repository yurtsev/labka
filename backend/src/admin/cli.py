import asyncio
import getpass
import logging
from uuid import UUID

from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider
from email_validator import EmailNotValidError, validate_email

from src.admin.accounts.dto import NewAdmin
from src.admin.accounts.service import AdminAccountService
from src.config import cfg
from src.core.di import AdminProvider, DbProvider, SecurityProvider
from src.core.errors import DomainError
from src.core.logging import setup_logging

log = logging.getLogger(__name__)


def ask_new_admin() -> NewAdmin:
    """Спрашивает данные админа в терминале; пароль вводится без эха и дважды."""
    try:
        email = validate_email(input("Почта: ").strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise SystemExit(f"Некорректная почта: {exc}") from exc
    last_name = input("Фамилия: ").strip()
    first_name = input("Имя: ").strip()
    middle_name = input("Отчество (можно пусто): ").strip() or None
    if not last_name or not first_name:
        raise SystemExit("Фамилия и имя обязательны")

    password = getpass.getpass("Пароль: ")
    if not cfg.auth.password_min_length <= len(password) <= cfg.auth.password_max_length:
        raise SystemExit(
            f"Пароль должен быть от {cfg.auth.password_min_length}"
            f" до {cfg.auth.password_max_length} символов"
        )
    if getpass.getpass("Пароль ещё раз: ") != password:
        raise SystemExit("Пароли не совпадают")

    return NewAdmin(
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        email=email.normalized.lower(),
        password=password,
    )


async def create_admin(new_admin: NewAdmin) -> UUID:
    container = make_async_container(
        FastapiProvider(), DbProvider(), SecurityProvider(), AdminProvider()
    )
    try:
        async with container() as request_container:
            service = await request_container.get(AdminAccountService)
            return await service.create_admin(new_admin)
    finally:
        await container.close()


def main() -> None:
    setup_logging(cfg.logging.level)
    new_admin = ask_new_admin()
    try:
        admin_id = asyncio.run(create_admin(new_admin))
    except DomainError as exc:
        raise SystemExit(exc.message) from exc
    log.info("admin.admin_created", extra={"user_id": str(admin_id)})


if __name__ == "__main__":
    main()
