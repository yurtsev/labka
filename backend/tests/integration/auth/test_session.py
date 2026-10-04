import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Session, User
from tests.support.auth import InvitedStudent, error_code


def client_with_refresh_token(app: FastAPI, refresh_token: str) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"refresh_token": refresh_token},
    )


@pytest.mark.case(id="UC-C2-001")
async def test_refresh_rotates_tokens_and_keeps_session(
    client: AsyncClient, db: AsyncSession, registered_student: InvitedStudent
) -> None:
    old_refresh = client.cookies["refresh_token"]

    response = await client.post("/api/auth/refresh")

    assert response.status_code == 204
    # Access-токен в ту же секунду может совпасть со старым: JWT детерминирован по iat/exp.
    assert set(response.cookies.keys()) == {"access_token", "refresh_token"}
    assert client.cookies["refresh_token"] != old_refresh
    assert (await client.get("/api/auth/me")).status_code == 200
    sessions = (await db.scalars(select(Session))).all()
    assert len(sessions) == 1
    assert sessions[0].revoked_at is None


@pytest.mark.case(id="UC-C2-002")
async def test_reused_refresh_token_revokes_session(
    app: FastAPI, client: AsyncClient, db: AsyncSession, registered_student: InvitedStudent
) -> None:
    stolen_refresh = client.cookies["refresh_token"]
    assert (await client.post("/api/auth/refresh")).status_code == 204

    async with client_with_refresh_token(app, stolen_refresh) as thief:
        reuse = await thief.post("/api/auth/refresh")

    assert reuse.status_code == 401
    assert error_code(reuse) == "auth.refresh_token_reused"
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.post("/api/auth/refresh")).status_code == 401
    session = await db.scalar(select(Session))
    assert session is not None and session.revoked_at is not None


@pytest.mark.case(id="UC-C2-003")
async def test_refresh_rejects_missing_and_malformed_tokens(
    app: FastAPI, client: AsyncClient
) -> None:
    missing = await client.post("/api/auth/refresh")
    async with client_with_refresh_token(app, "not-a-token") as malformed_client:
        malformed = await malformed_client.post("/api/auth/refresh")

    assert missing.status_code == malformed.status_code == 401
    assert error_code(missing) == error_code(malformed) == "auth.invalid_refresh_token"


@pytest.mark.case(id="UC-C3-001")
async def test_logout_revokes_both_tokens_of_session(
    app: FastAPI, client: AsyncClient, registered_student: InvitedStudent
) -> None:
    access = client.cookies["access_token"]
    refresh = client.cookies["refresh_token"]

    response = await client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "access_token" not in client.cookies
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"access_token": access, "refresh_token": refresh},
    ) as replay:
        assert (await replay.get("/api/auth/me")).status_code == 401
        assert (await replay.post("/api/auth/refresh")).status_code == 401


@pytest.mark.case(id="UC-C3-002")
async def test_logout_without_session_is_idempotent(client: AsyncClient) -> None:
    response = await client.post("/api/auth/logout")

    assert response.status_code == 204


@pytest.mark.case(id="AUTH-SESSION-001")
async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")

    assert response.status_code == 401
    assert error_code(response) == "security.not_authenticated"


@pytest.mark.case(id="AUTH-SESSION-002")
async def test_deactivated_user_loses_access_with_live_session(
    client: AsyncClient, db: AsyncSession, registered_student: InvitedStudent
) -> None:
    await db.execute(update(User).values(is_active=False))
    await db.commit()

    me = await client.get("/api/auth/me")
    refresh = await client.post("/api/auth/refresh")

    assert me.status_code == 401
    assert refresh.status_code == 401
    assert error_code(refresh) == "auth.account_deactivated"
