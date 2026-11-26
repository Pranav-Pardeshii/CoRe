# AGENTS.md — CoRe Repository Conventions

## Architecture

CoRe uses a feature-first modular monolith under `backend/app/`:
- `core/`: `config.py` (`pydantic-settings`), `security.py` (JWT via `PyJWT` & Argon2id via `pwdlib`), `rate_limit.py` (LRU sliding-window limiter), `logging.py` (JSON Cloud Logging), `exceptions.py` (global error handlers).
- `infrastructure/database/`: `base.py` (declarative `Base`), `session.py` (`DatabaseManager` + `get_db_session`), `model_registry.py` (imports all ORM models for Alembic).
- `modules/<feature>/`:
  - `models.py`: SQLAlchemy 2.x ORM mappings.
  - `schemas.py`: Pydantic v2 request/response contracts.
  - `router.py`: HTTP routing, dependency injection, no business logic or raw SQL.
  - `service.py`: Business logic and transaction boundaries (`commit()` / `rollback()`).
  - `repository.py`: Explicit SQLAlchemy 2.x queries; repositories must **not** commit independently.

## Rules for Changes

1. **Async DB in FastAPI only**: Use `AsyncSession` (`mysql+asyncmy://`). Never use `mysql.connector` in FastAPI request handlers, and never create engines or pools at module import time.
2. **ETL stays synchronous**: `etl/` (`python -m etl ...`) uses `mysql-connector-python` for batch processing. Never add `CREATE TABLE` or `ALTER TABLE` statements to `etl/load.py`; Alembic owns schema evolution.
3. **API compatibility**: Preserve endpoint paths and contracts used by `frontend/` (`/auth/*`, `/catalog/filters`, `/recommender/`, `/trends/`, `/saved-lists/`, `/`, `/ping`, `/health/live`, `/health/ready`).
4. **Configuration & secrets**: All backend configuration goes through `Settings` in `backend/app/core/config.py` (with `CORE_CORS_ORIGINS` including the Vite dev/production origin, e.g. `http://localhost:5173`), and frontend configuration goes through `VITE_API_BASE_URL` in `frontend/`. Never hardcode secrets, never auto-generate `SECRET_KEY`, and never disable SSL CA verification.
5. **Testing & quality**:
   - Python (`backend/`, `etl/`): Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run pytest -v` before finishing changes.
   - Frontend (`frontend/` React 19 + Vite + TypeScript): Run `npm run typecheck`, `npm run lint`, `npm run test`, and `npm run build` before finishing changes.
   - Integration tests require `CORE_TEST_DATABASE_URL` pointing to an isolated test MySQL database (database name must be `core_test` or end with `_test`, never production).
6. **PowerShell**: Use Windows PowerShell-compatible commands in docs and scripts.

### Large Dataset Handling
- Never read entire CSV, JSONL, or other large data files into context.
- Inspect schemas, column names, dtypes, and a maximum of 10–20 sample rows.
- Use Python scripts for dataset profiling and validation.
- Exclude generated datasets, build artifacts, caches, and large binary files from agent context.
- Never modify source datasets unless explicitly instructed.
