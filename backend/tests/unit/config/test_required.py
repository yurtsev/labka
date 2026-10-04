import pytest
from fastapi import FastAPI

from src.config import cfg
from src.config.exc import ConfigIncompleteError
from src.main import lifespan


@pytest.mark.case(id="CONFIG-001")
async def test_app_does_not_start_without_required_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cfg.auth, "jwt_secret", "")
    monkeypatch.setattr(cfg.s3, "endpoint_url", "")
    monkeypatch.setattr(cfg.s3, "bucket", "")
    monkeypatch.setattr(cfg.s3, "access_key", "")
    monkeypatch.setattr(cfg.s3, "secret_key", "")

    with pytest.raises(ConfigIncompleteError) as error:
        async with lifespan(FastAPI()):
            pass

    missing = error.value.context["missing_settings"]
    assert isinstance(missing, list)
    assert set(missing) >= {
        "auth.jwt_secret",
        "s3.endpoint_url",
        "s3.bucket",
        "s3.access_key",
        "s3.secret_key",
    }
