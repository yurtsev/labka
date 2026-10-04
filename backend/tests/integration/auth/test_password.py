import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.support.auth import InvitedStudent, error_code, login


@pytest.mark.case(id="UC-C4-001")
async def test_password_change_keeps_current_session_and_revokes_others(
    app: FastAPI, client: AsyncClient, registered_student: InvitedStudent
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as other:
        assert (
            await login(other, registered_student.email, registered_student.password)
        ).status_code == 200

        response = await client.post(
            "/api/auth/password",
            json={"current_password": registered_student.password, "new_password": "password-2"},
        )

        assert response.status_code == 204
        assert (await client.get("/api/auth/me")).status_code == 200
        assert (await other.get("/api/auth/me")).status_code == 401
        assert (await other.post("/api/auth/refresh")).status_code == 401
    old = await login(client, registered_student.email, registered_student.password)
    new = await login(client, registered_student.email, "password-2")
    assert old.status_code == 401
    assert new.status_code == 200


@pytest.mark.case(id="UC-C4-002")
async def test_password_change_rejects_wrong_current_password(
    client: AsyncClient, registered_student: InvitedStudent
) -> None:
    response = await client.post(
        "/api/auth/password",
        json={"current_password": "wrong-password", "new_password": "password-2"},
    )

    assert response.status_code == 422
    assert error_code(response) == "auth.wrong_current_password"
    assert (
        await login(client, registered_student.email, registered_student.password)
    ).status_code == 200


@pytest.mark.case(id="UC-C4-003")
async def test_password_change_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/password",
        json={"current_password": "password-1", "new_password": "password-2"},
    )

    assert response.status_code == 401


@pytest.mark.case(id="UC-C4-004")
async def test_too_long_password_is_rejected(
    client: AsyncClient, registered_student: InvitedStudent
) -> None:
    too_long = "x" * 33

    signed_in = await login(client, registered_student.email, too_long)
    changed = await client.post(
        "/api/auth/password",
        json={"current_password": registered_student.password, "new_password": too_long},
    )

    assert signed_in.status_code == 422
    assert changed.status_code == 422
    assert error_code(changed) == "request.invalid"
