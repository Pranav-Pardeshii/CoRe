import os
from urllib.parse import urlparse

import pytest
from backend.app.core.config import Settings

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_FORBIDDEN_HOST_MARKERS = ("aivencloud.com", "prod", "production")


def _allowed_remote_hosts() -> set[str]:
    raw = os.getenv("CORE_TEST_ALLOWED_HOSTS", "")
    return {host.strip().lower() for host in raw.split(",") if host.strip()}


def get_validated_test_database_url() -> str:
    """Return CORE_TEST_DATABASE_URL after strict fail-closed checks, or skip when unset."""
    url = os.getenv("CORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("CORE_TEST_DATABASE_URL is not set; skipping MySQL integration tests.")

    parsed = urlparse(url)
    if parsed.scheme != "mysql+asyncmy":
        pytest.fail(
            f"CORE_TEST_DATABASE_URL must use 'mysql+asyncmy://' scheme, got {parsed.scheme!r}."
        )

    host = (parsed.hostname or "").lower()
    if not host:
        pytest.fail("CORE_TEST_DATABASE_URL must include a hostname.")

    if any(marker in host for marker in _FORBIDDEN_HOST_MARKERS):
        pytest.fail(f"Refusing to run integration tests against forbidden host: {host!r}.")

    if host not in _LOOPBACK_HOSTS and host not in _allowed_remote_hosts():
        pytest.fail(
            f"Refusing to run integration tests against non-loopback host {host!r} "
            "without explicit CORE_TEST_ALLOWED_HOSTS allowlisting."
        )

    db_name = parsed.path.lstrip("/").lower()
    if not db_name or (db_name != "core_test" and not db_name.endswith("_test")):
        pytest.fail(
            "CORE_TEST_DATABASE_URL database name must be 'core_test' or end with '_test', "
            f"got {db_name!r}."
        )

    return url


def require_destructive_test_opt_in() -> None:
    """Fail closed before destructive schema-reset tests unless explicitly opted in."""
    opt_in = os.getenv("CORE_TEST_ALLOW_DESTRUCTIVE", "").strip().lower()
    if opt_in not in {"1", "true", "yes"}:
        pytest.fail("Destructive MySQL integration tests require CORE_TEST_ALLOW_DESTRUCTIVE=1.")


@pytest.fixture
def test_settings() -> Settings:
    """Isolated settings for unit tests without touching backend/.env."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_HOST="localhost",
        DB_USER="test_user",
        DB_PORT=3306,
        DB_PASS="test_pass",
        DB_NAME="core_test",
        DB_SSL_CA=None,
        SECRET_KEY="unit-test-secret-key-do-not-use-in-prod",
    )
