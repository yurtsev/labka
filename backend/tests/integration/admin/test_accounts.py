import pytest
from httpx import AsyncClient

from src.admin.accounts.dto import NewAdmin
from src.admin.accounts.service import AdminAccountService
from src.admin.exc.accounts import AdminEmailTakenError
from tests.support.admin import admin_login


async def create_admin_via_command(new_admin: NewAdmin) -> None:
    """То же, что делает `make create-admin` после ввода данных."""
    from src.main import container

    async with container() as request_container:
        service = await request_container.get(AdminAccountService)
        await service.create_admin(new_admin)


@pytest.mark.case(id="ADMIN-ACCOUNT-001")
async def test_created_admin_signs_in(client: AsyncClient) -> None:
    new_admin = NewAdmin(
        last_name="Админов",
        first_name="Админ",
        middle_name=None,
        email="root@example.com",
        password="root-password-1",
    )

    await create_admin_via_command(new_admin)
    response = await admin_login(client, new_admin.email, new_admin.password)

    assert response.status_code == 302
    with pytest.raises(AdminEmailTakenError):
        await create_admin_via_command(new_admin)
