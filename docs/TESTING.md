# Testing Guide

## Test Suite Structure (`backend/tests/`)

- `test_config_and_app.py`: Settings validation (`SECRET_KEY`), URL encoding, SSL context verification, app lifespan/root/ping, and `SQLAlchemyError` non-disclosure.
- `test_security_and_auth.py`: Bcrypt hashing, JWT non-mutation and expiry checks, `get_current_user_id`, registration conflicts, and uniform `401` login responses.
- `test_recommendations_and_trends.py`: Percentile `0–100` bounds, `All` wildcard mapping, pagination offsets, `GOPENS` trend default, and HTTP contracts.
- `test_saved_lists.py`: Duplicate reorder ID rejection, ownership enforcement, duplicate-item `IntegrityError` rollback, rank allocation, and auth requirements.
- `test_mysql_integration.py` (`@pytest.mark.integration`): End-to-end Alembic `downgrade`/`upgrade` and real MySQL queries across all features.

## Running Unit Tests (PowerShell)

```powershell
uv run pytest -v
```

Without `CORE_TEST_DATABASE_URL` set, unit tests run and integration tests are explicitly skipped.

## Running MySQL Integration Tests (PowerShell)

Point `CORE_TEST_DATABASE_URL` to an isolated local or CI test MySQL database whose name includes `test`:

```powershell
$env:CORE_TEST_DATABASE_URL = "mysql+asyncmy://user:password@localhost:3306/core_test"
uv run pytest -v
```

## Linting & Type Checking

```powershell
uv run ruff check backend
uv run pyright
```
