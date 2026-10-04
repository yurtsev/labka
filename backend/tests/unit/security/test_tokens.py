from datetime import UTC, datetime, timedelta
from uuid import uuid7

import jwt
import pytest

from src.config import cfg
from src.core.security.dto import AccessTokenClaims
from src.core.security.exc import MalformedRefreshTokenError, NotAuthenticatedError
from src.core.security.service import SecurityService


@pytest.mark.case(id="AUTH-TOKEN-001")
def test_access_token_roundtrip_carries_user_and_session() -> None:
    security = SecurityService()
    claims = AccessTokenClaims(user_id=uuid7(), session_id=uuid7())

    assert security.decode_access_token(security.issue_access_token(claims)) == claims


@pytest.mark.case(id="AUTH-TOKEN-002")
@pytest.mark.parametrize(
    "payload_update",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"sid": "not-a-uuid"},
    ],
    ids=["expired", "bad-session-id"],
)
def test_invalid_access_token_is_rejected(payload_update: dict[str, object]) -> None:
    payload: dict[str, object] = {
        "sub": str(uuid7()),
        "sid": str(uuid7()),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        **payload_update,
    }
    token = jwt.encode(payload, cfg.auth.jwt_secret, algorithm="HS256")

    with pytest.raises(NotAuthenticatedError):
        SecurityService().decode_access_token(token)


@pytest.mark.case(id="AUTH-TOKEN-003")
def test_access_token_signed_with_other_secret_is_rejected() -> None:
    claims = {
        "sub": str(uuid7()),
        "sid": str(uuid7()),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(claims, "attacker-secret-attacker-secret-attacker", algorithm="HS256")

    with pytest.raises(NotAuthenticatedError):
        SecurityService().decode_access_token(token)


@pytest.mark.case(id="AUTH-TOKEN-004")
def test_refresh_token_roundtrip_and_hash_check() -> None:
    security = SecurityService()
    issued = security.issue_refresh_token(uuid7())
    stored_hash = security.hash_token(issued.secret)

    parsed = security.parse_refresh_token(str(issued))

    assert parsed == issued
    assert security.verify_token(parsed.secret, stored_hash)
    assert not security.verify_token("other-secret", stored_hash)


@pytest.mark.case(id="AUTH-TOKEN-005")
@pytest.mark.parametrize("token", ["", "no-dot", "not-a-uuid.secret", f"{uuid7()}."])
def test_malformed_refresh_token_is_rejected(token: str) -> None:
    with pytest.raises(MalformedRefreshTokenError):
        SecurityService().parse_refresh_token(token)


@pytest.mark.case(id="AUTH-PASSWORD-001")
def test_password_hash_is_salted_and_verifiable() -> None:
    security = SecurityService()

    first = security.hash_password("password-1")
    second = security.hash_password("password-1")

    assert first != second
    assert first.startswith("$argon2")
    assert security.verify_password(first, "password-1")
    assert not security.verify_password(first, "password-2")
    assert not security.verify_password("not-a-hash", "password-1")
