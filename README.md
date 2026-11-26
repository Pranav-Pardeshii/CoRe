# CoRe (College Recommendation & Analytics Platform)

CoRe is an MHT-CET engineering college recommendation and cutoff-analytics application built with FastAPI, MySQL, SQLAlchemy 2.x (async), Alembic, and Streamlit.

## Features

- **College Recommendations (`GET /recommender/`)**: Filter eligible colleges and branches by percentile (`0–100`), category, branch, and division across the latest 2 distinct admission years in MySQL (or `CORE_RECOMMENDER_YEARS`) with `min_cutoff` / `max_cutoff` aggregation and single-query pagination.
- **Catalog Filters (`GET /catalog/filters`)**: Dynamic categories, branches, divisions, years, and levels queried directly from MySQL.
- **Cutoff Trends (`GET /trends/`)**: View historical Stage I cutoff trends across years, CAP rounds, and seat `level`s (defaults `All` category to `GOPENS`).
- **Authentication (`POST /auth/register`, `POST /auth/login`)**: Custom JWT (`HS256`, configurable `CORE_ACCESS_TOKEN_EXPIRE_MINUTES`, default 60 minutes) with `Argon2id` password hashing via `pwdlib`.
- **Saved Lists (`GET/POST/PUT /saved-lists/`, `DELETE /saved-lists/{id}`)**: Authenticated per-user college shortlist (up to 100 items) with bulk reorder and ownership enforcement.

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI, Pydantic v2, `pydantic-settings` |
| ORM & Driver | SQLAlchemy 2.x async ORM, `asyncmy` |
| Auth & Crypto | `pwdlib[argon2]`, `PyJWT[crypto]` |
| Migrations | Alembic |
| Database | MySQL 8.0 (Google Cloud SQL for production) |
| Hosting & Secrets | Google Cloud Run, Artifact Registry, Secret Manager |
| Frontend | Streamlit, Altair (`frontend` dependency group) |
| ETL | Python CLI (`python -m etl`), `mysql-connector-python` (`etl` dependency group) |
| Tooling | `uv`, `pytest`, `ruff`, `pyright` |

## Getting Started (Windows PowerShell)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Poppler (`pdftotext`) on `PATH` if running PDF extraction

### 1. Install Dependencies

```powershell
uv sync --all-groups
```

### 2. Configure Environment

Copy `backend\.env.example` to `backend\.env` and fill in your database credentials and a strong `CORE_SECRET_KEY` (32+ characters in production):

```powershell
Copy-Item backend\.env.example backend\.env
```

### 3. Initialize a Fresh Database (Local or Cloud SQL)

```powershell
uv run alembic -c backend/alembic.ini upgrade head
uv run python -m etl run --pdf-dir PDFs --output-dir csvs --csv-path cutoffs_flat.csv
```

> Note: `PDFs/`, `csvs/`, and `cutoffs_flat.csv` are gitignored and must be present locally before running the ETL pipeline.

### 4. Run the Backend

```powershell
uv run uvicorn backend.main:create_app --factory --reload
```

### 5. Run the Frontend (separate terminal)

```powershell
$env:CORE_API_BASE_URL = "http://127.0.0.1:8000"
uv run streamlit run frontend/ui.py
```

### 6. Run Checks & Tests

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -v
```

To run MySQL integration tests against an isolated test database:

```powershell
$env:CORE_TEST_DATABASE_URL = "mysql+asyncmy://root:password@127.0.0.1:3306/core_test"
$env:CORE_TEST_ALLOW_DESTRUCTIVE = "1"
uv run pytest -v
```

## Cloud Run + Cloud SQL Deployment Notes

- Build the slim backend image with `docker build -t core-backend .` (installs backend runtime dependencies only via `uv sync --frozen --no-dev`).
- Connect Cloud Run to Cloud SQL using `CORE_DB_UNIX_SOCKET=/cloudsql/<PROJECT>:<REGION>:<INSTANCE>` (leave `CORE_DB_HOST` unset) and set `CORE_TRUSTED_PROXY_HOPS=1`.
- **Connection Pool Sizing**: Each Cloud Run instance runs `--workers 1` with `CORE_DB_POOL_SIZE=2` and `CORE_DB_MAX_OVERFLOW=3` (max 5 connections/instance). Set Cloud Run `--max-instances` so `max_instances * 5` stays comfortably below Cloud SQL `max_connections` (e.g. `--max-instances=15` -> at most 75 connections, leaving headroom for Alembic and ETL).

## Documentation

Engineering documentation lives in `docs/`:
- [PRD](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Contracts](docs/API.md)
- [Database & Migrations](docs/DATABASE.md)
- [Architecture Decisions](docs/DECISIONS.md)
- [Testing Guide](docs/TESTING.md)
- [Progress & Readiness](docs/PROGRESS.md)

## License

This project is licensed under the [MIT License](LICENSE).
