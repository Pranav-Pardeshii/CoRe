# CoRe — MHT-CET College Recommendation & CAP Analytics Platform

CoRe is a full-stack web application and PDF-to-MySQL data pipeline for exploring Maharashtra MHT-CET engineering college cutoffs, inspecting historical CAP round trends, and building ordered CAP Option Form shortlists.

MHT-CET Centralized Admission Process (CAP) cutoffs are published as multi-hundred-page PDF matrices spanning hundreds of institutions, 100+ seat category codes (such as `GOPENS`, `LOBCH`, and `DEFRNT1S`), multiple seat allocation levels, and percentiles reported to 7 decimal places. CoRe parses those official reports into a normalized MySQL 8.0 schema, serves eligibility and trend queries through an async FastAPI service, and presents a responsive React 19 interface tailored for students and families comparing options.

---

## Core Capabilities

- **7-Decimal Eligibility Recommender (`GET /recommender/`)**: Evaluates Stage I cutoffs across the latest 2 distinct admission years in MySQL (or `CORE_RECOMMENDER_YEARS`) using `MIN(percentile) <= user_percentile`, returning `min_cutoff`, `max_cutoff`, and total matches via single-query `COUNT(*) OVER()` windowed pagination (`page_size` `5–30`).
- **Dynamic Catalog & Seat Decoding (`GET /catalog/filters`)**: Serves distinct categories, branches, divisions, years, and seat levels from MySQL with a 600-second in-process TTL cache; the frontend decodes raw CAP codes and seat levels (`SL`, `HU_HU`, `HU_OHU`, `OHU_HU`, `OHU_OHU`) into plain-English labels.
- **Multi-Round Cutoff Trends (`GET /trends/`)**: Queries historical Stage I closing percentiles ordered by `(admission_year, cap_round, level)`, defaulting `All` category queries to `GOPENS`, and renders seat-level-isolated Recharts line series with exact-value reference tables.
- **Authenticated CAP Option Form Shortlist (`/auth/*`, `/saved-lists/`)**: Supports up to 100 saved college-branch items per user with `Argon2id` password hashing, `HS256` JWT authentication, drag-and-drop (`@dnd-kit`) and step-button reordering, CSV export with formula-injection escaping, and `@media print` A4 formatting.
- **PDF-to-MySQL ETL CLI (`python -m etl`)**: Runs single-pass Poppler `pdftotext` extraction, coordinate-based wrapped-header merging, zero-padded code normalization, fail-closed `Decimal` validation, and chunked `ON DUPLICATE KEY UPDATE` MySQL loading.

> **Preview status:** The repository does not include UI screenshots or recorded terminal demos yet. Adding screenshots of the Explorer ledger, Trends drawer, and Print Option Form view under a `docs/assets/` directory would improve visual inspection.

---

## System Architecture

CoRe is structured as an offline batch ETL pipeline feeding a MySQL 8.0 database, paired with a feature-first modular monolith API (`backend/app/`) and a standalone React 19 SPA (`frontend/`).

```mermaid
flowchart LR
    subgraph BatchETL["Offline Batch Pipeline (python -m etl)"]
        PDFs["CAP Cutoff PDFs"] --> Extract["etl/extract.py\nPoppler pdftotext -layout"]
        Extract --> Transform["etl/transform.py\nZero-pad + Division Map"]
        Transform --> Validate["etl/validate.py\nFail-closed Decimal & Key Gate"]
        Validate --> Load["etl/load.py\nmysql-connector-python Upsert"]
    end

    subgraph Client["Frontend SPA (frontend/)"]
        UI["React 19 + Vite + Tailwind v4\nExplorer / Trends / Shortlist"]
        TQ["TanStack Query + AbortController\nSessionStorage JWT"]
        UI --> TQ
    end

    subgraph API["FastAPI Backend (backend/app/)"]
        MW["Middleware\nCORS + Security Headers +\nX-Request-ID / Cloud Trace"]
        RL["InMemoryRateLimiter\nO(1) LRU + Proxy IP/Hop Extraction"]
        ModAuth["modules/auth\nArgon2id + PyJWT HS256"]
        ModCat["modules/catalog\n600s TTL Filter Cache"]
        ModRec["modules/recommendations\nWindowed Pagination Query"]
        ModTr["modules/trends\nStage I Multi-Level Series"]
        ModList["modules/saved_lists\nRow-Locked Bulk CASE Reorder"]
        DBMgr["DatabaseManager\nLifespan AsyncEngine (asyncmy)"]

        MW --> RL
        RL --> ModAuth
        RL --> ModCat
        RL --> ModRec
        RL --> ModTr
        MW --> ModList
        ModAuth --> DBMgr
        ModCat --> DBMgr
        ModRec --> DBMgr
        ModTr --> DBMgr
        ModList --> DBMgr
    end

    MySQL[("MySQL 8.0\nAlembic Migrations 0001-0004")]

    Load -->|"2,000-row chunked\nON DUPLICATE KEY UPDATE"| MySQL
    TQ -->|"HTTPS / JSON + Bearer JWT"| MW
    DBMgr -->|"mysql+asyncmy://\nTCP/TLS or Cloud SQL Unix Socket"| MySQL
```

### Request & Data-Flow Highlights

1. **ETL Ingestion & Data Integrity**: `etl/extract.py` resolves a Poppler `pdftotext` binary (explicitly rejecting Xpdf builds that misalign columns), invokes `pdftotext -layout -enc UTF-8` once per PDF, joins multi-line branch names, and merges wrapped category header suffixes 1-to-1 by 0-based character coordinate. `etl/transform.py` preserves leading zeros on 5-digit college codes and 10+ digit branch codes, maps 2-digit prefixes to Maharashtra's six DTE divisions, and deduplicates composite keys. `etl/validate.py` checks every row before `etl/load.py` verifies `alembic_version` and schema tables exist and commits 2,000-row upserts.
2. **Saved Shortlist Concurrency & Ordering**: Every shortlist mutation (`POST /saved-lists/`, `DELETE /saved-lists/{id}`, `PUT /saved-lists/`) locks the parent `users` row via `SELECT ... FOR UPDATE` to serialize concurrent modifications per account, enforces the 100-item limit and ownership checks, and updates `sort_order` across the entire list in a single `UPDATE ... SET sort_order = CASE ... END` statement.

```mermaid
sequenceDiagram
    actor User
    participant SPA as React Frontend
    participant Router as FastAPI Router & Auth
    participant Service as SavedListService
    participant DB as MySQL 8.0

    User->>SPA: Drag/step reorder shortlist
    SPA->>Router: PUT /saved-lists/ (Bearer JWT, ordered_list)
    Router->>Router: Verify HS256 JWT (iss/aud/exp/type) & extract user_id
    Router->>Service: reorder(session, user_id, ordered_list)
    Service->>Service: Reject duplicate IDs (400/422)
    Service->>DB: SELECT id FROM users WHERE id = :uid FOR UPDATE
    Service->>DB: SELECT id FROM saved_list_items WHERE user_id = :uid FOR UPDATE
    alt Missing or unowned IDs
        Service->>DB: ROLLBACK
        Service-->>SPA: 400 Invalid Input -> Refresh shortlist
    else Exact owned ID set
        Service->>DB: UPDATE saved_list_items SET sort_order = CASE id ... END
        Service->>DB: COMMIT
        Service-->>SPA: 200 OK
    end
```

---

## Database Schema

Schema migrations live in `backend/migrations/versions/` (`0001_initial_schema` through `0004_production_hardening`) with predictable constraint naming defined in [base.py](backend/app/infrastructure/database/base.py).

```mermaid
erDiagram
    colleges ||--o{ branches : "college_code"
    branches ||--o{ admission_cutoffs : "branch_code"
    users ||--o{ saved_list_items : "user_id (ON DELETE CASCADE)"
    branches ||--o{ saved_list_items : "branch_code"

    colleges {
        varchar(10) college_code PK
        varchar(300) college_name
        varchar(300) status
        varchar(100) division
    }

    branches {
        varchar(15) branch_code PK
        varchar(300) branch_name
        varchar(10) college_code FK
    }

    admission_cutoffs {
        int id PK
        varchar(15) branch_code FK
        smallint admission_year
        tinyint cap_round
        varchar(10) level
        varchar(5) admission_stage
        varchar(20) category
        int merit_rank
        decimal(10_7) percentile
        timestamp created_at
    }

    users {
        int id PK
        varchar(100) username UK
        varchar(255) password_hash
        timestamp created_at
        timestamp updated_at
    }

    saved_list_items {
        int id PK
        int user_id FK
        varchar(10) college_code
        varchar(15) branch_code FK
        varchar(300) college_name
        varchar(300) branch_name
        int sort_order
        timestamp created_at
        timestamp updated_at
    }
```

Key constraints and indexes verified in [models.py](backend/app/modules/catalog/models.py), [auth/models.py](backend/app/modules/auth/models.py), and [saved_lists/models.py](backend/app/modules/saved_lists/models.py):
- `admission_cutoffs`: `DECIMAL(10, 7)` percentile with `CHECK (percentile >= 0 AND percentile <= 100)`, `UNIQUE (branch_code, admission_year, cap_round, level, admission_stage, category)`, and covering indexes `ix_admission_cutoffs_recommender`, `ix_admission_cutoffs_stage_year_branch`, and `ix_admission_cutoffs_trends`.
- `saved_list_items`: `UNIQUE (user_id, branch_code)`, `CHECK (sort_order >= 1)`, and `ix_saved_list_items_user_sort_order`. Denormalizes `college_code`, `college_name`, and `branch_name` so `GET /saved-lists/` executes as a single-table indexed read without joins.

---

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Backend API | FastAPI, Pydantic v2, `pydantic-settings`, Uvicorn | Async HTTP routing, request/response validation, lifespan resource management, OpenAPI docs (non-production) |
| ORM & Async DB | SQLAlchemy 2.x (`asyncio`), `asyncmy`, Alembic | Async MySQL queries, connection pool management, and schema migrations (`0001`–`0004`) |
| Security & Auth | `pwdlib[argon2]`, `PyJWT[crypto]` | Argon2id password hashing (offloaded via `asyncio.to_thread`) and `HS256` JWT issuance/validation |
| Database | MySQL 8.0 | Relational storage for catalog, cutoffs, user accounts, and ordered shortlists |
| ETL Pipeline | Python 3.12 CLI (`python -m etl`), Poppler `pdftotext`, `mysql-connector-python` | Synchronous PDF layout parsing, normalization, validation, and chunked MySQL upserts |
| Frontend SPA | React 19, TypeScript, Vite, Tailwind CSS v4 | Editorial ledger UI, URL-synced filters, 7-decimal input, `@media print` Option Form, CSV export |
| Frontend State & UI | TanStack Query v5, Recharts, `@dnd-kit`, Lucide Icons | Request caching/cancellation, multi-year seat-level trend charts, accessible drag-and-drop & step reordering |
| Quality & CI | `uv`, Ruff, Pyright, Pytest, `httpx`, ESLint, Vitest, GitHub Actions | Linting, formatting, static type checking, unit tests, MySQL 8.0 integration tests, Docker build check |

---

## Project Structure

```text
CoRe/
├── .github/workflows/ci.yml      # CI: Python lint/unit, MySQL 8.0 integration, Docker build, frontend checks
├── backend/
│   ├── alembic.ini               # Alembic configuration
│   ├── .env.example              # Backend & ETL environment variable template
│   ├── main.py                   # ASGI factory re-export (backend.main:create_app)
│   ├── app/
│   │   ├── main.py               # create_app() factory, lifespan DB init, middleware, health routes
│   │   ├── api/v1/router.py      # Aggregates feature module routers
│   │   ├── core/                 # config.py, security.py, rate_limit.py, logging.py, exceptions.py
│   │   ├── infrastructure/       # Declarative Base, DatabaseManager, get_db_session, model_registry
│   │   └── modules/              # Feature modules: auth, catalog, recommendations, trends, saved_lists
│   ├── migrations/               # Alembic async env.py and revisions 0001–0004
│   └── tests/                    # Unit tests + fail-closed MySQL integration suite
├── etl/
│   ├── cli.py                    # Subcommands: extract, transform, validate, load, run
│   ├── config.py                 # Sync MySQL config (CORE_DB_* / legacy fallback) and SSL CA resolution
│   ├── extract.py                # Single-pass Poppler pdftotext parser & wrapped-header merger
│   ├── transform.py              # Leading-zero normalization, division prefix mapping, deduplication
│   ├── validate.py               # Fail-closed Decimal, regex, range, and composite-key checks
│   ├── load.py                   # Chunked ON DUPLICATE KEY UPDATE loader
│   └── tests/                    # Unit tests for extraction, transform/validation, config, and loader
├── frontend/
│   ├── .env.example              # Frontend VITE_API_BASE_URL template
│   ├── package.json              # React 19 + Vite scripts (dev, typecheck, lint, test, build)
│   └── src/
│       ├── api/                  # Fetch client with timeout/error mapping, authSession, QueryClient, types
│       ├── components/           # FilterBar, CollegeResults, TrendsSheet, ShortlistView, AuthModal/Panel
│       ├── context/              # AuthContext & inline input validation
│       ├── hooks/                # useCatalogFilters, useSavedShortlist (optimistic updates)
│       └── lib/                  # Category/level decoder, 7-decimal formatters, CSV export, URL filter sync
├── docs/                         # PRD, architecture, API contracts, DB schema, ADRs, testing notes
├── Dockerfile                    # Multi-stage non-root backend container (uv sync --frozen --no-dev)
└── pyproject.toml                # Python 3.12 dependencies, dependency groups (etl, dev), Ruff & Pyright config
```

---

## Installation & Getting Started

### Prerequisites

- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)**
- **Node.js 22+** and **npm** (for `frontend/`)
- **MySQL 8.0** (local instance or Cloud SQL)
- **Poppler (`pdftotext`)** on `PATH` (only required when running `etl extract` / `etl run` on PDFs; Xpdf `pdftotext` builds are rejected)
- **Local CAP Cutoff PDFs** placed in `PDFs/` (gitignored; required only if populating a fresh database via ETL)

### 1. Clone and Install Python Dependencies

```powershell
git clone <repository-url>
cd CoRe
uv sync --all-groups
```

### 2. Configure Environment Variables

Copy the templates for both backend and frontend:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Edit `backend\.env` with your MySQL credentials and a `CORE_SECRET_KEY` (32+ characters required when `CORE_ENVIRONMENT=production`). Ensure `CORE_CORS_ORIGINS` includes your frontend origin (default `["http://localhost:5173","http://127.0.0.1:5173"]`).

### 3. Initialize the Database Schema & Load Data

Run Alembic migrations first (never skip straight to `alembic stamp` on an empty database), then run the ETL pipeline if you have local CAP PDFs in `PDFs/`:

```powershell
uv run alembic -c backend/alembic.ini upgrade head
uv run alembic -c backend/alembic.ini check
uv run python -m etl run --pdf-dir PDFs --output-dir csvs --csv-path cutoffs_flat.csv
```

If you already have a validated `cutoffs_flat.csv`, you can run `uv run python -m etl load --csv-path cutoffs_flat.csv` (or add `--dry-run` to validate and count records without writing to MySQL).

### 4. Start the Backend and Frontend

Backend (from repository root):

```powershell
uv run uvicorn backend.main:create_app --factory --reload
```

Frontend (in a second terminal):

```powershell
Set-Location frontend
npm ci
npm run dev
```

The API listens on `http://127.0.0.1:8000` (interactive OpenAPI docs at `/docs` when `CORE_ENVIRONMENT != "production"`) and the Vite dev server runs on `http://localhost:5173`.

On Linux/macOS shells, replace `Copy-Item` with `cp` and `Set-Location` with `cd`.

---

## Configuration

Backend configuration is validated by `Settings` in [config.py](backend/app/core/config.py) from environment variables or `backend/.env` (both `CORE_*` primary names and unprefixed legacy aliases are accepted).

| Variable | Purpose | Default / Required |
|---|---|---|
| `CORE_ENVIRONMENT` | Runtime mode (`development`, `testing`, `production`) | `development` |
| `CORE_LOG_LEVEL` | Application log level | `INFO` |
| `CORE_GCP_PROJECT_ID` | Enables Cloud Logging `logging.googleapis.com/trace` format (`GOOGLE_CLOUD_PROJECT` fallback) | Optional (`None`) |
| `CORE_CORS_ORIGINS` | Allowed frontend origins (`*` rejected in `production`) | `["http://localhost:5173","http://127.0.0.1:5173"]` |
| `CORE_TRUSTED_PROXY_IPS` | Trusted proxy IPs/CIDRs for `X-Forwarded-For` client IP resolution | `[]` |
| `CORE_TRUSTED_PROXY_HOPS` | Trusted proxy hop count from right of `X-Forwarded-For` (set `1` on Cloud Run) | `0` |
| `CORE_DB_HOST` / `CORE_DB_PORT` | MySQL TCP host and port (required unless `CORE_DB_UNIX_SOCKET` is set) | `None` / `3306` |
| `CORE_DB_UNIX_SOCKET` | Cloud SQL Unix socket path, e.g. `/cloudsql/<PROJECT>:<REGION>:<INSTANCE>` | Optional (`None`) |
| `CORE_DB_USER` / `CORE_DB_PASS` / `CORE_DB_NAME` | MySQL credentials and database name | Required |
| `CORE_DB_SSL_CA` | Path to SSL CA certificate for TCP TLS verification (relative to repo root or `backend/`) | Optional (`None`) |
| `CORE_DB_POOL_SIZE` / `CORE_DB_MAX_OVERFLOW` | Per-process SQLAlchemy async pool size and overflow | `2` / `3` |
| `CORE_DB_POOL_TIMEOUT` / `CORE_DB_CONNECT_TIMEOUT` / `CORE_DB_POOL_RECYCLE` | Pool wait, connect timeout, and recycle interval in seconds | `5` / `5` / `1800` |
| `CORE_SECRET_KEY` | JWT `HS256` signing secret (must be >= 32 chars in `production`) | Required |
| `CORE_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime in minutes | `60` |
| `CORE_AUTH_RATE_LIMIT_MAX_REQUESTS` / `CORE_AUTH_RATE_LIMIT_WINDOW_SECONDS` | Per-IP sliding window for `/auth/*` | `20` / `60` |
| `CORE_AUTH_LOGIN_USERNAME_MAX_ATTEMPTS` | Per-username failed-login threshold per window | `10` |
| `CORE_PUBLIC_RATE_LIMIT_MAX_REQUESTS` / `CORE_PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | Per-IP sliding window for `/ping`, `/catalog/filters`, `/recommender/`, `/trends/` | `60` / `60` |
| `CORE_RECOMMENDER_YEARS` | Explicit JSON list of admission years to query (unset = latest 2 distinct years in DB) | Optional (`None`) |
| `VITE_API_BASE_URL` | Frontend (`frontend/.env`) backend base URL without trailing slash | `http://127.0.0.1:8000` |

Integration test environment variables (used only by `backend/tests/test_mysql_integration.py`): `CORE_TEST_DATABASE_URL`, `CORE_TEST_ALLOW_DESTRUCTIVE`, and optional `CORE_TEST_ALLOWED_HOSTS`.

---

## API & CLI Overview

### HTTP Endpoints

| Method & Path | Auth | Cache / Rate Limit | Summary |
|---|---|---|---|
| `GET /` | Public | — | Service banner (`{"message": "MHT-CET College Predictor"}`) |
| `GET \| HEAD /ping` | Public | Public RL | Executes `SELECT 1`; returns `{"status": "ok"}` |
| `GET /health/live` | Public | — | Process liveness probe (`{"status": "alive"}`, no DB call) |
| `GET /health/ready` | Public | 2s TTL cache | Executes `SELECT 1`; returns `200` (`ready`) or `503` (`unavailable`) |
| `POST /auth/register` | Public | Auth RL | JSON `{username, password}` (`3–50` chars `[A-Za-z0-9_.-]`, `8–128` char password); `409` on duplicate |
| `POST /auth/login` | Public | Auth RL + Username throttle | Form-encoded `OAuth2PasswordRequestForm`; returns `Bearer` JWT (`401` timing-equalized) |
| `GET /catalog/filters` | Public | Public RL, `max-age=3600`, 600s server cache | Returns `{categories, branches, divisions, years, levels}` |
| `GET /recommender/` | Public | Public RL, `max-age=3600` | Query params: `percentile` (`0–100`), `category`, `branch`, `division`, `page` (`>=1`), `page_size` (`5–30`) |
| `GET /trends/` | Public | Public RL, `max-age=3600` | Query params: `branch_code`, `category` (`All` -> `GOPENS`), optional `level` |
| `GET /saved-lists/` | Bearer JWT | `Cache-Control: no-store` | Returns `{saved_list: [{id, college_name, branch_name}]}` ordered by `sort_order` |
| `POST /saved-lists/` | Bearer JWT | `Cache-Control: no-store` | Body `{branch_code}`; enforces 100-item cap (`400`) and duplicate guard (`409`) |
| `PUT /saved-lists/` | Bearer JWT | `Cache-Control: no-store` | Body `{ordered_list: [id, ...]}`; atomically reorders all owned items |
| `DELETE /saved-lists/{id}` | Bearer JWT | `Cache-Control: no-store` | Deletes owned item (`404` if missing or owned by another user) |

Full request/response contracts are documented in [docs/API.md](docs/API.md).

### ETL CLI Commands

```powershell
uv run python -m etl extract   --pdf-dir PDFs --output-dir csvs
uv run python -m etl transform --output-dir csvs --csv-path cutoffs_flat.csv
uv run python -m etl validate  --csv-path cutoffs_flat.csv
uv run python -m etl load      --csv-path cutoffs_flat.csv --batch-size 2000 --dry-run
uv run python -m etl run       --pdf-dir PDFs --output-dir csvs --csv-path cutoffs_flat.csv
```

---

## Testing & Quality Assurance

All linting, formatting, type-checking, and unit tests pass locally without a live MySQL server; integration tests require an isolated MySQL 8.0 test database and fail closed on non-`_test` names or production/Aiven hosts.

### Backend & ETL Checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -v -m "not integration"
```

To run the MySQL 8.0 integration suite (`backend/tests/test_mysql_integration.py`, covering `0001 -> head -> 0003 -> head` Alembic roundtrips, `alembic check`, `DECIMAL(10, 7)` fidelity, foreign-key/unique constraints, and end-to-end HTTP flows):

```powershell
$env:CORE_TEST_DATABASE_URL = "mysql+asyncmy://root:password@127.0.0.1:3306/core_test"
$env:CORE_TEST_ALLOW_DESTRUCTIVE = "1"
uv run pytest -v
```

### Frontend Checks

```powershell
Set-Location frontend
npm run typecheck
npm run lint
npm run test
npm run build
```

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs four jobs on pushes and pull requests to `main`: `lint-and-unit`, `mysql-integration` (against `mysql:8.0`), `docker-build`, and `frontend`.

---

## Deployment & Containerization

CoRe is live at **[core-frontend-six.vercel.app](https://core-frontend-six.vercel.app)**, deployed on the following free-tier stack:

| Component | Service | Notes |
|---|---|---|
| Frontend SPA | **Vercel Hobby** | Root directory `frontend/`, Vite preset, `VITE_API_BASE_URL` env var |
| Backend API | **Render Free Web Service** | Docker runtime using [`Dockerfile`](Dockerfile), `--workers 1` |
| Database | **TiDB Cloud Starter** | MySQL-compatible, `5 GiB` free, connects via TCP TLS (`CORE_DB_SSL_CA=ca.pem`) |
| Keep-Alive | **cron-job.org** | `GET /health/live` every 10 minutes to prevent Render's 15-minute idle sleep |

### Local Docker Build

```powershell
docker build -t core-backend .
```

### Render (Backend) Configuration

The [`Dockerfile`](Dockerfile) is multi-stage, runs as a non-root user, and listens on `$PORT` (default `8080`). Key environment variables for Render:

- `CORE_ENVIRONMENT=production` — enforces `CORE_SECRET_KEY` ≥ 32 chars and rejects `*` in `CORE_CORS_ORIGINS`.
- `CORE_TRUSTED_PROXY_HOPS=1` — resolves per-client IPs from Render's proxy `X-Forwarded-For`.
- `CORE_DB_HOST` / `CORE_DB_PORT=4000` / `CORE_DB_SSL_CA=/etc/secrets/ca.pem` — TiDB Cloud Starter TCP TLS connection.
- Upload `ca.pem` as a **Render Secret File** (mounted at `/etc/secrets/ca.pem`).
- Set Health Check Path to `/health/live`.

### TiDB Cloud Starter (Database)

TiDB Cloud Starter is MySQL-compatible and always free (no credit card, `5 GiB` row storage, `50M` Request Units/month). The ETL `ON DUPLICATE KEY UPDATE` syntax uses `VALUES(col)` for compatibility with both TiDB and MySQL 8.0.

To migrate and load data into TiDB from Windows (uses `WindowsSelectorEventLoopPolicy` to work around a Windows `asyncmy` + TLS incompatibility with `ProactorEventLoop`):

```powershell
# 1. Set env to point at TiDB (or update backend/.env)
$env:CORE_DB_SSL_CA = "./ca.pem"

# 2. Run Alembic migrations
uv run python -c "import asyncio; asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()); from alembic.config import main; main(['-c', 'backend/alembic.ini', 'upgrade', 'head'])"

# 3. Load cutoff data (277,424 rows across 386 colleges and 2,371 branches)
uv run python -m etl load
```

### Vercel (Frontend) Configuration

- **Root Directory:** `frontend`
- **Framework Preset:** Vite (Build Command `npm run build`, Output Directory `dist`)
- **Environment Variable:** `VITE_API_BASE_URL=https://<your-render-url>.onrender.com` (no trailing slash)

After deploying, update `CORE_CORS_ORIGINS` on Render to `["https://<your-vercel-domain>.vercel.app"]`.

> **Note:** `ca.pem` and `backend/.env` are gitignored and must be supplied manually in each deployment environment.

---

## Engineering Decisions & Trade-offs

1. **Async FastAPI (`asyncmy`) + Synchronous Batch ETL (`mysql-connector-python`)**: Keeping FastAPI fully async avoids blocking the event loop on database I/O, while isolating `mysql-connector-python` in the `etl` dependency group keeps batch `executemany` ingestion simple and prevents accidental sync DB usage in HTTP handlers. *Trade-off:* Two MySQL drivers are maintained across dependency groups.
2. **Process-Local Sliding-Window Rate Limiter & Lookup Caches**: `InMemoryRateLimiter` (`OrderedDict`, 10,000-key LRU bound), `CatalogRepository` filter cache (600s TTL), `RecommendationsRepository` latest-years cache (600s TTL), and `/health/ready` probe cache (2s TTL) eliminate external Redis infrastructure for single-node or moderate traffic. *Trade-off:* Rate-limit counters are per Cloud Run instance (global edge limits require Cloud Armor or a shared store), and newly loaded ETL data can take up to 600s to appear in cached filter/year metadata without a process restart.
3. **Denormalized Display Fields on `saved_list_items`**: Storing `college_code`, `college_name`, and `branch_name` alongside the `branch_code` foreign key makes `GET /saved-lists/` a single-table indexed lookup. *Trade-off:* `GET /saved-lists/` omits `branch_code` in its response schema, and upstream college/branch renames in `colleges`/`branches` do not automatically update previously saved items.
4. **Dummy-Hash Timing Equalization on Login**: `AuthService.login` runs `Argon2id` verification against a precomputed dummy hash when a username does not exist and returns identical `401` payloads for missing users and bad passwords, preventing username enumeration via response differences or timing side channels. *Trade-off:* Unknown-username login attempts incur one Argon2id verification cost, mitigated by per-IP and per-username rate limits.

---

## Limitations & Known Gaps

- **No Guest Shortlist Persistence**: Unlike the draft proposal in `frontend/PRODUCT.md`, the implemented React shortlist requires an authenticated account (`/saved-lists/`); unauthenticated visitors are prompted to sign in or register.
- **Stage I Focus**: `/recommender/` and `/trends/` intentionally filter `admission_stage == "I"` cutoffs, and `/trends/` maps `"All"` category queries to `"GOPENS"`.
- **Uncommitted / Gitignored Data Artifacts**: Source CAP PDFs (`PDFs/`), intermediate CSVs (`csvs/`), `cutoffs_flat.csv`, `.env` files, and `ca.pem` are gitignored; a fresh clone starts with an empty schema until ETL is executed locally against an external database (see [Deployment](#deployment--containerization)).
- **Legacy References in `docs/`**: While `README.md` and `.github/workflows/ci.yml` reflect the React 19 + Vite frontend, several files under `docs/` (`API.md`, `PRD.md`, `PROGRESS.md`, `TESTING.md`) still mention the retired Streamlit prototype.

---

## Documentation & License

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Contracts](docs/API.md)
- [Database Schema & Migrations](docs/DATABASE.md)
- [Architecture Decisions](docs/DECISIONS.md)
- [Testing Guide](docs/TESTING.md)
- [Frontend Product Spec](frontend/PRODUCT.md) & [Design System](frontend/DESIGN.md)

Licensed under the [MIT License](LICENSE).
