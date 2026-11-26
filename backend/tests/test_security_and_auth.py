from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import InMemoryRateLimiter, get_auth_rate_limiter
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError


def test_password_hashing_and_verification() -> None:
    hashed = hash_password("S3cur3P@ss!")
    assert hashed.startswith("$2b$")
    assert verify_password("S3cur3P@ss!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token_does_not_mutate_input_and_sets_expiry() -> None:
    payload = {"sub": "42", "username": "pranav"}
    token = create_access_token(payload, secret_key="secret", expires_minutes=15)

    assert "exp" not in payload
    decoded = decode_access_token(token, secret_key="secret")
    assert decoded["sub"] == "42"
    assert decoded["username"] == "pranav"
    assert "exp" in decoded


def test_decode_access_token_rejects_expired_token() -> None:
    expired_payload = {
        "sub": "1",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(expired_payload, "secret", algorithm="HS256")
    with pytest.raises(JWTError):
        decode_access_token(token, secret_key="secret")


def test_get_current_user_id_valid_and_invalid(test_settings: Settings) -> None:
    token = create_access_token({"sub": "7"}, secret_key=test_settings.SECRET_KEY)
    assert get_current_user_id(token=token, settings=test_settings) == 7

    bad_sub_token = create_access_token({"sub": "not-an-int"}, secret_key=test_settings.SECRET_KEY)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(token=bad_sub_token, settings=test_settings)
    assert exc_info.value.status_code == 401


def test_register_and_login_prevent_username_enumeration(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as client:
        # Unknown user -> 401 generic error
        no_user_result = MagicMock()
        no_user_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = no_user_result

        resp_missing = client.post("/auth/login", data={"username": "nobody", "password": "pw"})
        assert resp_missing.status_code == 401

        # Wrong password -> same 401 generic error
        existing_user = SimpleNamespace(
            id=5,
            username="pranav",
            password=hash_password("correct-pw"),
        )
        found_result = MagicMock()
        found_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = found_result

        resp_wrong_pw = client.post("/auth/login", data={"username": "pranav", "password": "bad"})
        assert resp_wrong_pw.status_code == 401
        assert resp_missing.json() == resp_wrong_pw.json()

        # Correct password -> 200 bearer token
        resp_ok = client.post("/auth/login", data={"username": "pranav", "password": "correct-pw"})
        assert resp_ok.status_code == 200
        body = resp_ok.json()
        assert body["token_type"] == "bearer"
        claims = decode_access_token(body["access_token"], secret_key=test_settings.SECRET_KEY)
        assert claims["sub"] == "5"
        assert claims["username"] == "pranav"

        # Duplicate registration -> 400 ConflictError + rollback
        mock_session.flush.side_effect = IntegrityError("INSERT", {}, Exception("Duplicate"))
        resp_dup = client.post("/auth/register", json={"username": "pranav", "password": "pw"})
        assert resp_dup.status_code == 400
        assert resp_dup.json() == {"detail": "Username already exists."}
        mock_session.rollback.assert_awaited()


def test_auth_rate_limiter_enforces_limit(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    limiter = InMemoryRateLimiter()
    mock_session = AsyncMock()
    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = no_user_result

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_auth_rate_limiter] = lambda: limiter

    with TestClient(app) as client:
        for _ in range(test_settings.AUTH_RATE_LIMIT_MAX_REQUESTS):
            resp = client.post("/auth/login", data={"username": "nobody", "password": "pw"})
            assert resp.status_code == 401
        blocked = client.post("/auth/login", data={"username": "nobody", "password": "pw"})
        assert blocked.status_code == 429
