# AGENTS.md — CoRe Repository Conventions

## Architecture

CoRe uses a feature-first modular monolith under `backend/app/`:
- `core/`: `config.py` (`pydantic-settings`), `security.py` (JWT & bcrypt), `exceptions.py` (global error handlers).
- `infrastructure/database/`: `base.py` (declarative `Base`), `session.py` (`DatabaseManager` + `get_db_session`), `model_registry.py` (imports all ORM models for Alembic).
- `modules/<feature>/`:
  - `models.py`: SQLAlchemy 2.x ORM mappings.
  - `schemas.py`: Pydantic v2 request/response contracts.
  - `router.py`: HTTP routing, dependency injection, no business logic or raw SQL.
  - `service.py`: Business logic and transaction boundaries (`commit()` / `rollback()`).
  - `repository.py`: Explicit SQLAlchemy 2.x queries; repositories must **not** commit independently.

## Rules for Changes

1. **Async DB in FastAPI only**: Use `AsyncSession` (`mysql+asyncmy://`). Never use `mysql.connector` in FastAPI request handlers, and never create engines or pools at module import time.
2. **ETL stays synchronous**: `etl/` uses `mysql-connector-python` for batch processing. Do not add `CREATE TABLE` or `ALTER TABLE` statements to `etl/loader.py`; Alembic owns schema evolution.
3. **API compatibility**: Preserve existing endpoint paths and response shapes used by `frontend/` (`/auth/*`, `/recommender/`, `/trends/`, `/saved-lists/`, `/`, `/ping`).
4. **Configuration & secrets**: All configuration goes through `Settings` in `backend/app/core/config.py`. Never hardcode secrets, never auto-generate `SECRET_KEY`, and never disable SSL CA verification.
5. **Testing & quality**:
   - Run `uv run ruff check backend`, `uv run pyright`, and `uv run pytest -v` before finishing changes.
   - Integration tests require `CORE_TEST_DATABASE_URL` pointing to an isolated test MySQL database (database name must contain `test`, never production/Aiven).
6. **PowerShell**: Use Windows PowerShell-compatible commands in docs and scripts.
