import os
from urllib.parse import urlparse

import pytest
from backend.app.core.config import Settings

_FORBIDDEN_HOST_MARKERS = ("aivencloud.com", "prod", "production")


def get_validated_test_database_url() -> str:
    """Return CORE_TEST_DATABASE_URL after fail-closed safety checks, or skip."""
    url = os.getenv("CORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("CORE_TEST_DATABASE_URL is not set; skipping MySQL integration tests.")

    parsed = urlparse(url)
    if parsed.scheme != "mysql+asyncmy":
        pytest.fail(
            f"CORE_TEST_DATABASE_URL must use 'mysql+asyncmy://' scheme, got {parsed.scheme!r}."
        )

    host = (parsed.hostname or "").lower()
    if any(marker in host for marker in _FORBIDDEN_HOST_MARKERS):
        pytest.fail(f"Refusing to run integration tests against forbidden host: {host!r}.")

    db_name = parsed.path.lstrip("/").lower()
    if "test" not in db_name:
        pytest.fail(
            f"CORE_TEST_DATABASE_URL database name must contain 'test' for safety, got {db_name!r}."
        )

    return url


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
