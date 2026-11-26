# Testing Guide

## Test Suite Structure

- `backend/tests/`:
  - `test_config_and_app.py`: Settings validation (including production `SECRET_KEY` and CORS rules, `DB_UNIX_SOCKET`), SSL verification, `/health/live`, `/health/ready`, security headers, `X-Request-ID` sanitization, `SQLAlchemyError` & unhandled 500 JSON handlers.
  - `test_security_and_auth.py`: Argon2id hashing, PyJWT claims/expiry, `get_current_user_id`, timing-safe dummy-hash login, input validation, uniform `401` responses, LRU rate limiter, and `TRUSTED_PROXY_IPS` / `TRUSTED_PROXY_HOPS`.
  - `test_recommendations_and_trends.py`: Percentile `0–100` bounds, `All` wildcard mapping, pagination offsets, `GOPENS` trend default, `level` field, and `GET /catalog/filters` contract.
  - `test_saved_lists.py`: Duplicate reorder ID rejection, ownership enforcement, 100-item limit, user-row lock check, duplicate-item `409 ConflictError`, and bulk `CASE` reorder.
  - `test_mysql_integration.py` (`@pytest.mark.integration`): `0001` -> `head` -> `0003` -> `head` migration roundtrip, `alembic check`, `DECIMAL(10, 7)` precision, multi-item reorder, pagination, `GET /catalog/filters`, and `trends` with multiple `level`s.
- `etl/tests/`:
  - `test_extract.py`, `test_transform_and_validate.py`, `test_load_and_config.py`: Wrapped header merging, multi-line branch joining, single-pass `pdftotext`, leading-zero preservation, unmapped division rejection, validator rules, chunked `executemany`, and CLI exit codes.
- `frontend/tests/`:
  - `test_frontend.py`: `decode_category` coverage and `api_client` network, non-JSON, `422`/`409`, `401` session-reset, and timeout/route checks.

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
