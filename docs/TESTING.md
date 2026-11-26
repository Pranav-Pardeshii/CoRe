# Testing Guide

## Test Suite Structure (`backend/tests/`)

- `test_config_and_app.py`: Settings validation, URL encoding, SSL verification, `/health/live`, `/health/ready`, `SQLAlchemyError` non-disclosure, and integration safety guard checks.
- `test_security_and_auth.py`: Bcrypt hashing, JWT non-mutation and expiry, `get_current_user_id`, uniform `401` login responses, rate-limiter bucket pruning, and `CORE_TRUSTED_PROXY_IPS` handling.
- `test_recommendations_and_trends.py`: Percentile `0–100` bounds, `All` wildcard mapping, pagination offsets, `GOPENS` trend default, and HTTP contracts.
- `test_saved_lists.py`: Duplicate reorder ID rejection, ownership enforcement, duplicate-item `IntegrityError` rollback, `sort_order` allocation, and auth requirements.
- `test_mysql_integration.py` (`@pytest.mark.integration`): End-to-end Alembic `0001` -> `0003` data preservation, empty DB -> `head`, `alembic check`, and real MySQL queries.

## Running Unit Tests (PowerShell)

```powershell
uv run pytest -v
```

Without `CORE_TEST_DATABASE_URL` set, unit tests run and integration tests are skipped.

## Running MySQL Integration Tests (PowerShell)

Integration tests fail closed unless **all** of the following hold:
1. `CORE_TEST_DATABASE_URL` uses `mysql+asyncmy://`.
2. The host is loopback (`localhost`, `127.0.0.1`, `::1`) or explicitly listed in `CORE_TEST_ALLOWED_HOSTS` (forbidden production/Aiven hosts are always rejected).
3. The database name is `core_test` or ends with `_test`.
4. `CORE_TEST_ALLOW_DESTRUCTIVE=1` is explicitly set for schema-reset tests.

```powershell
$env:CORE_TEST_DATABASE_URL = "mysql+asyncmy://root@127.0.0.1:13306/core_test"
$env:CORE_TEST_ALLOW_DESTRUCTIVE = "1"
uv run pytest -v
```

## Linting & Type Checking

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
