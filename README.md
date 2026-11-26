# CoRe (College Recommendation & Analytics Platform)

CoRe is an MHT-CET engineering college recommendation and cutoff-analytics application built with FastAPI, MySQL, SQLAlchemy 2.x (async), Alembic, and Streamlit.

## Features

- **College Recommendations (`GET /recommender/`)**: Filter eligible colleges and branches by percentile (`0–100`), category, branch, and division across 2024–2025 Stage I CAP cutoffs with `min_cutoff` / `max_cutoff` aggregation and pagination.
- **Cutoff Trends (`GET /trends/`)**: View historical Stage I cutoff trends across years and CAP rounds (defaults `All` category to `GOPENS`).
- **Authentication (`POST /auth/register`, `POST /auth/login`)**: Custom JWT (`HS256`, 15-minute access tokens) with `bcrypt` password hashing.
- **Saved Lists (`GET/POST/PUT /saved-lists/`, `DELETE /saved-lists/{id}`)**: Authenticated per-user college shortlist with rank ordering and ownership enforcement.

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI, Pydantic v2, `pydantic-settings` |
| ORM & Driver | SQLAlchemy 2.x async ORM, `asyncmy` |
| Migrations | Alembic |
| Database | MySQL (Google Cloud SQL for production) |
| Hosting & Secrets | Google Cloud Run, Artifact Registry, Secret Manager |
| Frontend | Streamlit, Altair |
| ETL | Python, `mysql-connector-python` (batch) |
| Tooling | `uv`, `pytest`, `ruff`, `pyright` |

## Getting Started (Windows PowerShell)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Install Dependencies

```powershell
uv sync
```

### 2. Configure Environment

Copy `backend\.env.example` to `backend\.env` and fill in your database credentials, SSL CA path (e.g. `./ca.pem`), and a strong `SECRET_KEY`:

```powershell
Copy-Item backend\.env.example backend\.env
```

### 3. Initialize a Fresh Database (Local or Cloud SQL)

```powershell
uv run alembic -c backend/alembic.ini upgrade head
uv run python etl/loader.py
```

> Note: `PDFs/`, `csvs/`, and `cutoffs_flat.csv` are gitignored and must be present locally before running `etl/loader.py`.

### 4. Run the Backend

```powershell
uv run uvicorn backend.main:app --reload
```

### 5. Run the Frontend (separate terminal)

```powershell
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
