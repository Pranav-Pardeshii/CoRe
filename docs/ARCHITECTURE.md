# Architecture

## Backend Structure (`backend/app/`)

CoRe follows a feature-first modular monolith:

```text
backend/app/
├── api/v1/router.py             # Aggregates feature routers
├── core/
│   ├── config.py                # pydantic-settings (CORE_*), Unix socket/TCP, SSL, CORS, pool sizing
│   ├── logging.py               # Cloud Logging JSON formatter with validated X-Request-ID & trace
│   ├── rate_limit.py            # O(1) LRU sliding-window limiter with CIDR + proxy-hop IP extraction
│   ├── security.py              # Argon2id hashing (pwdlib), HS256 JWT (PyJWT) with iss/aud/iat/type
│   └── exceptions.py            # AppError hierarchy (409 ConflictError) & sanitized 500 handlers
├── infrastructure/database/
│   ├── base.py                  # Shared DeclarativeBase with constraint naming convention
│   ├── session.py               # DatabaseManager (lifespan engine) & get_db_session
│   └── model_registry.py        # Imports all ORM models for Alembic metadata
├── modules/
│   ├── auth/                    # User model, register/login router, service, repo
│   ├── catalog/                 # College, Branch, AdmissionCutoff models, /catalog/filters router & repo
│   ├── recommendations/         # Dynamic-year eligibility query, windowed pagination, service, router
│   ├── trends/                  # Historical cutoff trend query (with level), service, router
│   └── saved_lists/             # SavedListItem model, parent-locked CRUD, bulk CASE reorder
└── main.py                      # create_app() factory + lifespan + security headers + health endpoints
```

`backend/main.py` exports `create_app` for `uvicorn backend.main:create_app --factory` (without creating an app at module import time).

## Layer Responsibilities

- **Routers**: HTTP request parsing, `Depends(...)` injection (`get_app_settings`, `get_db_session`), cache headers, response model serialization.
- **Schemas**: Pydantic v2 validation and response contracts.
- **Services**: Business rules and transaction boundaries (`await session.commit()` / `await session.rollback()`).
- **Repositories**: Explicit SQLAlchemy 2.x queries. Repositories never commit transactions.
- **Infrastructure**: Single `AsyncEngine` per process, initialized in FastAPI `lifespan` and disposed on shutdown. Each request receives its own `AsyncSession`.

## Production Deployment Architecture (Google Cloud)

- **Database**: Google Cloud SQL for MySQL 8.0 (`mysql+asyncmy://` over `CORE_DB_UNIX_SOCKET`).
- **Backend Hosting**: Google Cloud Run (`--workers 1`, `CORE_TRUSTED_PROXY_HOPS=1`, `CORE_DB_POOL_SIZE=2`, `CORE_DB_MAX_OVERFLOW=3`).
- **Pool Sizing Math**: Max 5 connections per Cloud Run instance (`2 + 3`). With `--max-instances=15`, peak backend connections are 75, leaving safe headroom on a 100-connection Cloud SQL instance for Alembic and ETL.
- **Secrets**: Google Cloud Secret Manager (`CORE_SECRET_KEY`, database credentials).
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`: lint/unit, MySQL 8.0 integration, Docker build).
- **Edge Rate Limiting**: Because `InMemoryRateLimiter` is process-local, global rate limiting across scaled Cloud Run instances should be enforced at Cloud Armor / load balancer.
