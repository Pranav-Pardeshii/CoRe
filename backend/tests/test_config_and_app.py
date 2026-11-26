import ssl
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from backend.app.core.config import Settings
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from backend.tests.conftest import (
    get_validated_test_database_url,
    require_destructive_test_opt_in,
)
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError


def test_settings_requires_non_empty_secret_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            DB_HOST="localhost",
            DB_USER="user",
            DB_PASS="pass",
            DB_NAME="core_test",
            SECRET_KEY="   ",
        )


def test_settings_production_requires_strong_secret_and_no_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="32 characters"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            ENVIRONMENT="production",
            DB_HOST="localhost",
            DB_USER="user",
            DB_PASS="pass",
            DB_NAME="core_test",
            SECRET_KEY="too-short",
            CORS_ORIGINS=["https://core.example.com"],
        )

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            ENVIRONMENT="production",
            DB_HOST="localhost",
            DB_USER="user",
            DB_PASS="pass",
            DB_NAME="core_test",
            SECRET_KEY="a" * 32,
            CORS_ORIGINS=["*"],
        )


def test_settings_supports_unix_socket_without_host() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_UNIX_SOCKET="/cloudsql/proj:region:inst",
        DB_USER="user",
        DB_PASS="pass",
        DB_NAME="core_db",
        SECRET_KEY="secret",
    )
    url = settings.async_database_url
    assert url.host is None
    assert url.port is None
    assert url.database == "core_db"


def test_settings_url_handles_special_characters() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_HOST="localhost",
        DB_USER="user@domain",
        DB_PORT=3307,
        DB_PASS="p@ss:w/rd#1?",
        DB_NAME="core_test",
        SECRET_KEY="secret",
    )
    url = settings.async_database_url
    assert url.drivername == "mysql+asyncmy"
    assert url.username == "user@domain"
    assert url.password == "p@ss:w/rd#1?"
    assert url.port == 3307
    assert "p%40ss%3Aw%2Frd%231%3F" in url.render_as_string(hide_password=False)


def test_settings_ssl_context_missing_file_raises(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_HOST="localhost",
        DB_USER="user",
        DB_PASS="pass",
        DB_NAME="core_test",
        DB_SSL_CA=str(tmp_path / "missing-ca.pem"),
        SECRET_KEY="secret",
    )
    with pytest.raises(FileNotFoundError):
        settings.build_ssl_context()


def test_settings_ssl_context_uses_verification_when_ca_exists() -> None:
    ca_file = Path("ca.pem")
    if not ca_file.exists():
        pytest.skip("ca.pem not present in workspace")

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_HOST="localhost",
        DB_USER="user",
        DB_PASS="pass",
        DB_NAME="core_test",
        DB_SSL_CA="./ca.pem",
        SECRET_KEY="secret",
    )
    ctx = settings.build_ssl_context()
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_app_root_ping_and_security_headers(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    with TestClient(app) as client:
        home_resp = client.get("/")
        assert home_resp.status_code == 200
        assert home_resp.json() == {"message": "MHT-CET College Predictor"}
        assert home_resp.headers["X-Content-Type-Options"] == "nosniff"
        assert home_resp.headers["X-Frame-Options"] == "DENY"
        assert home_resp.headers["Referrer-Policy"] == "no-referrer"

        ping_resp = client.get("/ping")
        assert ping_resp.status_code == 200
        assert ping_resp.json() == {"status": "ok"}
        assert "X-Request-ID" in ping_resp.headers

        # Reject CRLF/invalid X-Request-ID and replace with generated hex ID
        bad_req_id = "bad\r\ninjected-header"
        sanitized_resp = client.get("/health/live", headers={"X-Request-ID": bad_req_id})
        assert sanitized_resp.status_code == 200
        assert sanitized_resp.headers["X-Request-ID"] != bad_req_id
        assert len(sanitized_resp.headers["X-Request-ID"]) == 32

        ready_resp = client.get("/health/ready")
        assert ready_resp.status_code == 200
        assert ready_resp.json() == {"status": "ready"}
        assert mock_session.execute.await_count == 2


def test_readiness_returns_503_without_leaking_db_details(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()
    mock_session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("secret-db-host"),
    )

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    with TestClient(app) as client:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json() == {"status": "unavailable"}
        assert "secret-db-host" not in resp.text


def test_sqlalchemy_and_unexpected_errors_return_sanitized_json_500(
    test_settings: Settings,
) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()
    mock_session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("secret-internal-host-or-credential-detail"),
    )

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    @app.get("/_boom")
    async def boom() -> None:
        raise RuntimeError("sensitive internal stack message")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/ping")
        assert resp.status_code == 500
        assert resp.json() == {"detail": "A database error occurred."}
        assert "secret-internal-host-or-credential-detail" not in resp.text

        unhandled = client.get("/_boom")
        assert unhandled.status_code == 500
        assert unhandled.json() == {"detail": "Internal server error."}
        assert "sensitive internal stack message" not in unhandled.text


@pytest.mark.parametrize(
    "bad_url",
    [
        "mysql+asyncmy://u:p@mysql-core.aivencloud.com:10944/core_test",
        "mysql+asyncmy://u:p@prod-db.example.com:3306/core_test",
        "mysql+asyncmy://u:p@unknown-remote.example.com:3306/core_test",
        "mysql+pymysql://u:p@localhost:3306/core_test",
        "sqlite+aiosqlite:///test.db",
        "mysql+asyncmy://u:p@localhost:3306/defaultdb",
        "mysql+asyncmy://u:p@localhost:3306/test_app",
    ],
)
def test_integration_safety_guard_rejects_unsafe_urls(
    monkeypatch: pytest.MonkeyPatch,
    bad_url: str,
) -> None:
    monkeypatch.delenv("CORE_TEST_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("CORE_TEST_DATABASE_URL", bad_url)
    with pytest.raises(pytest.fail.Exception):
        get_validated_test_database_url()


@pytest.mark.parametrize(
    "loopback_url",
    [
        "mysql+asyncmy://root@127.0.0.1:13306/core_test",
        "mysql+asyncmy://root@localhost:3306/ci_test",
    ],
)
def test_integration_safety_guard_accepts_loopback_test_urls(
    monkeypatch: pytest.MonkeyPatch,
    loopback_url: str,
) -> None:
    monkeypatch.delenv("CORE_TEST_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("CORE_TEST_DATABASE_URL", loopback_url)
    assert get_validated_test_database_url() == loopback_url


def test_integration_safety_guard_allows_explicitly_allowlisted_remote_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_url = "mysql+asyncmy://ci:pw@ci-mysql.internal:3306/core_test"
    monkeypatch.setenv("CORE_TEST_DATABASE_URL", remote_url)
    monkeypatch.setenv("CORE_TEST_ALLOWED_HOSTS", "ci-mysql.internal")
    assert get_validated_test_database_url() == remote_url


def test_destructive_opt_in_fails_closed_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORE_TEST_ALLOW_DESTRUCTIVE", raising=False)
    with pytest.raises(pytest.fail.Exception):
        require_destructive_test_opt_in()

    monkeypatch.setenv("CORE_TEST_ALLOW_DESTRUCTIVE", "1")
    require_destructive_test_opt_in()
