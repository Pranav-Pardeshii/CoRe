# Progress & Production Readiness

## Completed in This Refactoring

- Restructured backend into `backend/app/` modular monolith (`core`, `infrastructure/database`, `modules/{auth,catalog,recommendations,trends,saved_lists}`, `api/v1`).
- Replaced import-time `mysql.connector` pool with lifespan-managed SQLAlchemy 2.x async engine (`asyncmy`) and per-request `AsyncSession`.
- Fixed critical bugs:
  - Import-time DB connection creation removed.
  - Username enumeration on `POST /auth/login` fixed (uniform `401`).
  - `SECRET_KEY` required and validated at startup; added to `backend/.env.example`.
  - `create_access_token` no longer mutates caller dicts.
  - `RecommenderQuery.percentile` aligned to `0–100` (`ge=0, le=100`).
  - `SavedListReorderRequest` and `SavedListService.reorder` reject duplicate IDs and enforce exact ownership.
  - `get_saved_list` no longer checks `cursor.rowcount` before fetching.
  - `SQLAlchemyError` handler prevents raw DB error disclosure.
- Configured Alembic with `0001_initial_schema` (legacy baseline) and `0002_standardize_schema` (renamed `admission_cutoffs`, `saved_list_items`, columns, check constraints, and query indexes), verified with `upgrade`, `downgrade`, `alembic check`, and legacy-to-new data preservation tests against MySQL 8.0.44.
- Hardened configuration (`CORE_` env prefix with legacy fallback), structured logging with `X-Request-ID`, CORS middleware, auth rate limiting (`429`), and `/health/live` + `/health/ready` endpoints.
- Updated `etl/loader.py` and `etl/add_location.py` for `admission_cutoffs` compatibility and proper resource cleanup.
- Verified `uv sync --locked`, `ruff check`, `ruff format --check`, `pyright`, and `pytest -v`.

## Remaining Gaps Before Full Production Readiness

1. **Aiven Schema Reconciliation**: Live Aiven MySQL (`mysql-core-core-v1.h.aivencloud.com:10944`) was unreachable from this environment (`socket.gaierror`). Inspect `SHOW CREATE TABLE` on Aiven for `users` and `saved_list` to confirm exact column lengths/constraint names before running `alembic stamp 0001_initial_schema`.
2. **ETL DDL Removal**: Remove `CREATE TABLE IF NOT EXISTS` from `etl/loader.py` once Alembic is stamped on production.
