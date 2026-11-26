# Progress & Production Readiness

## Completed

- **ETL Package (`etl/`)**: Replaced ad-hoc scripts with typed `python -m etl` CLI (`extract`, `transform`, `validate`, `load`, `run`), single-pass `pdftotext` extraction, 1-to-1 wrapped category header merging, multi-line branch joining, leading-zero preservation, fail-closed validation, and chunked `ON DUPLICATE KEY UPDATE` loading.
- **Backend Hardening (`backend/`)**:
  - Added Alembic `0004_production_hardening` (`DECIMAL(10, 7)` percentiles, `uq_users_username`, covering/lookup indexes, audit timestamps).
  - Removed import-time `create_app()` execution; added `get_app_settings`, Cloud SQL `DB_UNIX_SOCKET` support, and Cloud Run pool/timeout tuning.
  - Migrated to `pwdlib[argon2]` and `PyJWT[crypto]` with `asyncio.to_thread`, dummy-hash timing equalization, strict input validation, O(1) LRU rate limiting with `CORE_TRUSTED_PROXY_HOPS`, and per-username failed-login throttling.
  - Added Cloud Logging JSON formatting, `X-Request-ID` validation, security headers, `GET /catalog/filters`, `level` on `/trends/`, dynamic years + windowed pagination on `/recommender/`, and parent-row locking + bulk `CASE` reorder on `/saved-lists/`.
- **Frontend Refactor (`frontend/`)**: Added centralized `api_client.py` (`CORE_API_BASE_URL`, timeouts, safe JSON/network/401 handling), cross-user `saved_list_cache` cleanup, dynamic `/catalog/filters`, `GOPENS` default, `level`-aware Altair trend charts, and HTML escaping.
- **Packaging, Container & CI**: Separated `pyproject.toml` dependency groups (`etl`, `frontend`, `dev`), added slim multi-stage non-root `Dockerfile` + `.dockerignore`, `backend/.env.example`, and `.github/workflows/ci.yml`.

## Remaining Work for Google Cloud Deployment (Option A)

1. **Provision Cloud SQL for MySQL 8.0** and create an empty application database.
2. **Initialize schema & data**: Run `uv run alembic -c backend/alembic.ini upgrade head` and `uv run python -m etl run ...` against Cloud SQL, then verify row counts.
3. **Deploy to Cloud Run**: Push container to Artifact Registry, bind Secret Manager secrets (`CORE_SECRET_KEY`, DB credentials), attach Cloud SQL instance (`CORE_DB_UNIX_SOCKET`), and set `--workers 1` with `--max-instances` sized to Cloud SQL `max_connections`.
