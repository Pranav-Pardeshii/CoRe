# Progress & Production Readiness

## Completed

- Restructured backend into `backend/app/` modular monolith (`core`, `infrastructure/database`, `modules/{auth,catalog,recommendations,trends,saved_lists}`, `api/v1`).
- Replaced import-time `mysql.connector` pool with lifespan-managed SQLAlchemy 2.x async engine (`asyncmy`) and per-request `AsyncSession`.
- Standardized schema naming (`admission_cutoffs`, `saved_list_items`, `password_hash`, `sort_order`, `merit_rank`, `admission_year`, `cap_round`, `admission_stage`), constraints, and query indexes across Alembic revisions `0001`–`0003`.
- Hardened authentication, CORS, `CORE_` configuration, structured logging (`X-Request-ID`), bounded process-local auth rate limiting with `CORE_TRUSTED_PROXY_IPS`, and `/health/live` + `/health/ready` endpoints.
- Removed DDL from `etl/loader.py` and added Alembic schema-initialization verification.
- Verified `uv sync --locked`, `ruff check .`, `ruff format --check .`, `pyright`, and `pytest -v` (36 passed including MySQL 8.0 integration and `0001` -> `0003` migration tests).
- Confirmed source admission datasets (`PDFs/`, `csvs/`, and `cutoffs_flat.csv`) are present locally (gitignored) for fresh ETL ingestion.

## Remaining Work for Google Cloud Deployment (Option A)

1. **Provision Cloud SQL for MySQL** and create an empty application database.
2. **Initialize schema & data**: Run `alembic upgrade head` (no `stamp`) and `uv run python etl/loader.py` against Cloud SQL, then verify row counts and API endpoints.
3. **Containerize & deploy**: Add Dockerfile, Artifact Registry, Secret Manager bindings, Cloud Run service, and GitHub Actions CI/CD workflow.
4. **Decommission Aiven** only after the Google Cloud environment is verified.
