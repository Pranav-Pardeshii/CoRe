from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from backend.app.core.config import Settings
from backend.app.core.exceptions import UnauthorizedError
from backend.app.core.rate_limit import (
    InMemoryRateLimiter,
    extract_client_ip,
    get_auth_ip_rate_limiter,
    get_auth_username_rate_limiter,
)
from backend.app.core.security import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    decode_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from backend.app.modules.auth.schemas import UserRegisterRequest
from backend.app.modules.auth.service import AuthService
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def test_password_hashing_and_verification() -> None:
    hashed = hash_password("S3cur3P@ss!")
    assert hashed.startswith("$argon2id$")
    assert verify_password("S3cur3P@ss!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token_does_not_mutate_input_and_sets_claims() -> None:
    payload = {"sub": "42", "username": "pranav"}
    secret = "test-secret-key-at-least-32-bytes"
    token = create_access_token(payload, secret_key=secret, expires_minutes=15)

    assert "exp" not in payload
    decoded = decode_access_token(token, secret_key=secret)
    assert decoded["sub"] == "42"
    assert decoded["username"] == "pranav"
    assert decoded["iss"] == JWT_ISSUER
    assert decoded["aud"] == JWT_AUDIENCE
    assert decoded["type"] == "access"
    assert "exp" in decoded
    assert "iat" in decoded


def test_decode_access_token_rejects_expired_token() -> None:
    now = datetime.now(UTC)
    secret = "test-secret-key-at-least-32-bytes"
    expired_payload = {
        "sub": "1",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=1),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "access",
    }
    token = jwt.encode(expired_payload, secret, algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token, secret_key=secret)


def test_get_current_user_id_valid_and_invalid(test_settings: Settings) -> None:
    token = create_access_token({"sub": "7"}, secret_key=test_settings.SECRET_KEY)
    assert get_current_user_id(token=token, settings=test_settings) == 7

    bad_sub_token = create_access_token({"sub": "not-an-int"}, secret_key=test_settings.SECRET_KEY)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(token=bad_sub_token, settings=test_settings)
    assert exc_info.value.status_code == 401


def test_auth_input_validation_rules() -> None:
    req = UserRegisterRequest(username="  pranav_01  ", password="Password123!")
    assert req.username == "pranav_01"

    with pytest.raises(ValidationError):
        UserRegisterRequest(username="ab", password="Password123!")
    with pytest.raises(ValidationError):
        UserRegisterRequest(username="bad user!", password="Password123!")
    with pytest.raises(ValidationError):
        UserRegisterRequest(username="pranav", password="short")
    with pytest.raises(ValidationError):
        UserRegisterRequest(username="pranav", password="x" * 129)


async def test_timing_safe_login_verifies_dummy_hash_for_missing_user(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
) -> None:
    dummy_called = {"count": 0}

    def spy_dummy(plain: str) -> bool:
        dummy_called["count"] += 1
        return False

    monkeypatch.setattr("backend.app.modules.auth.service.verify_dummy_password", spy_dummy)

    repo = AsyncMock()
    repo.get_by_username.return_value = None
    service = AuthService(repository=repo)
    session = AsyncMock()

    with pytest.raises(UnauthorizedError):
        await service.login(session, username="missing", password="pw", settings=test_settings)

    assert dummy_called["count"] == 1


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
    app.dependency_overrides[get_auth_ip_rate_limiter] = lambda: InMemoryRateLimiter()

    with TestClient(app) as client:
        # Unknown user -> 401 generic error + no-store cache header
        no_user_result = MagicMock()
        no_user_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = no_user_result

        resp_missing = client.post("/auth/login", data={"username": "nobody", "password": "pw"})
        assert resp_missing.status_code == 401
        assert resp_missing.headers.get("Cache-Control") == "no-store"

        # Wrong password -> same 401 generic error
        existing_user = SimpleNamespace(
            id=5,
            username="pranav",
            password_hash=hash_password("correct-pw"),
        )
        found_result = MagicMock()
        found_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = found_result

        resp_wrong_pw = client.post("/auth/login", data={"username": "pranav", "password": "bad"})
        assert resp_wrong_pw.status_code == 401
        assert resp_missing.json() == resp_wrong_pw.json()

        # Overly long password -> rejected before hashing
        resp_long_pw = client.post(
            "/auth/login",
            data={"username": "pranav", "password": "x" * 200},
        )
        assert resp_long_pw.status_code == 401

        # Correct password -> 200 bearer token
        resp_ok = client.post("/auth/login", data={"username": "pranav", "password": "correct-pw"})
        assert resp_ok.status_code == 200
        body = resp_ok.json()
        assert body["token_type"] == "bearer"
        claims = decode_access_token(body["access_token"], secret_key=test_settings.SECRET_KEY)
        assert claims["sub"] == "5"
        assert claims["username"] == "pranav"

        # Duplicate registration -> 409 ConflictError + rollback
        mock_session.flush.side_effect = IntegrityError("INSERT", {}, Exception("Duplicate"))
        resp_dup = client.post(
            "/auth/register",
            json={"username": "pranav", "password": "Password123!"},
        )
        assert resp_dup.status_code == 409
        assert resp_dup.json() == {"detail": "Username already exists."}
        mock_session.rollback.assert_awaited()


def test_auth_rate_limiter_enforces_ip_and_username_limits(test_settings: Settings) -> None:
    proxy_settings = test_settings.model_copy(
        update={
            "TRUSTED_PROXY_HOPS": 1,
            "AUTH_RATE_LIMIT_MAX_REQUESTS": 4,
            "AUTH_LOGIN_USERNAME_MAX_ATTEMPTS": 3,
        }
    )
    app = create_app(
        settings=proxy_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    ip_limiter = InMemoryRateLimiter()
    username_limiter = InMemoryRateLimiter()
    mock_session = AsyncMock()
    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = no_user_result

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_auth_ip_rate_limiter] = lambda: ip_limiter
    app.dependency_overrides[get_auth_username_rate_limiter] = lambda: username_limiter

    with TestClient(app) as client:
        # (a) Per-IP limit across varying usernames
        for idx in range(proxy_settings.AUTH_RATE_LIMIT_MAX_REQUESTS):
            resp = client.post(
                "/auth/login",
                data={"username": f"nobody_{idx}", "password": "pw"},
                headers={"X-Forwarded-For": "198.51.100.10"},
            )
            assert resp.status_code == 401
        ip_blocked = client.post(
            "/auth/login",
            data={"username": "nobody_final", "password": "pw"},
            headers={"X-Forwarded-For": "198.51.100.10"},
        )
        assert ip_blocked.status_code == 429

        # (b) Per-username lockout across rotating client IPs
        for idx in range(proxy_settings.AUTH_LOGIN_USERNAME_MAX_ATTEMPTS):
            resp = client.post(
                "/auth/login",
                data={"username": "victim_user", "password": "wrong"},
                headers={"X-Forwarded-For": f"203.0.113.{idx + 1}"},
            )
            assert resp.status_code == 401
        username_blocked = client.post(
            "/auth/login",
            data={"username": "victim_user", "password": "wrong"},
            headers={"X-Forwarded-For": "203.0.113.200"},
        )
        assert username_blocked.status_code == 429


def test_rate_limiter_lru_eviction_and_proxy_extraction() -> None:
    limiter = InMemoryRateLimiter(max_keys=2)
    assert limiter.check_and_record("k1", max_requests=2, window_seconds=60)
    assert limiter.check_and_record("k2", max_requests=2, window_seconds=60)
    assert limiter.check_and_record("k3", max_requests=2, window_seconds=60)
    assert limiter.tracked_key_count == 2

    untrusted_req = SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.9"),
        headers={"X-Forwarded-For": "10.0.0.1"},
    )
    assert extract_client_ip(untrusted_req, ["10.1.1.1"]) == "203.0.113.9"  # type: ignore[arg-type]

    trusted_req = SimpleNamespace(
        client=SimpleNamespace(host="10.1.1.1"),
        headers={"X-Forwarded-For": "198.51.100.4, 10.1.1.1"},
    )
    assert extract_client_ip(trusted_req, ["10.1.1.0/24"]) == "198.51.100.4"  # type: ignore[arg-type]

    cloud_run_req = SimpleNamespace(
        client=SimpleNamespace(host="169.254.1.1"),
        headers={"X-Forwarded-For": "spoofed, 198.51.100.99"},
    )
    assert extract_client_ip(cloud_run_req, [], trusted_proxy_hops=1) == "198.51.100.99"  # type: ignore[arg-type]
