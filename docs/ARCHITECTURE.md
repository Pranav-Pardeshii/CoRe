# Architecture

## Backend Structure (`backend/app/`)

CoRe follows a feature-first modular monolith:

```text
backend/app/
├── api/v1/router.py             # Aggregates feature routers
├── core/
│   ├── config.py                # pydantic-settings (CORE_*), SSL context, CORS, trusted proxies
│   ├── logging.py               # Structured logging with request_id correlation
│   ├── rate_limit.py            # Process-local per-IP sliding-window auth rate limiter
│   ├── security.py              # bcrypt hashing, HS256 JWT creation/validation
│   └── exceptions.py            # AppError hierarchy & SQLAlchemyError handler
├── infrastructure/database/
│   ├── base.py                  # Shared DeclarativeBase with constraint naming convention
│   ├── session.py               # DatabaseManager (lifespan engine) & get_db_session
│   └── model_registry.py        # Imports all ORM models for Alembic metadata
├── modules/
│   ├── auth/                    # User model, register/login router, service, repo
│   ├── catalog/                 # College, Branch, AdmissionCutoff models & lookup repo
│   ├── recommendations/         # Eligibility query, pagination, service, router
│   ├── trends/                  # Historical cutoff trend query, service, router
│   └── saved_lists/             # SavedListItem model, CRUD, reorder, ownership
└── main.py                      # create_app() factory + lifespan + /, /ping, /health/*
```

`backend/main.py` re-exports `app` and `create_app` for `uvicorn backend.main:app` compatibility.

## Layer Responsibilities

- **Routers**: HTTP request parsing, `Depends(...)` injection, response model serialization.
- **Schemas**: Pydantic v2 validation and response contracts.
- **Services**: Business rules and transaction boundaries (`await session.commit()` / `await session.rollback()`).
- **Repositories**: Explicit SQLAlchemy 2.x queries. Repositories never commit transactions.
- **Infrastructure**: Single `AsyncEngine` per process, initialized in FastAPI `lifespan` and disposed on shutdown. Each request receives its own `AsyncSession`.

## Target Production Deployment Architecture

- **Database**: Google Cloud SQL for MySQL (`mysql+asyncmy://`).
- **Backend Hosting**: Google Cloud Run (containerized FastAPI via Artifact Registry).
- **Secrets**: Google Cloud Secret Manager (`CORE_SECRET_KEY`, database credentials).
- **CI/CD**: GitHub Actions.
- **Edge Rate Limiting**: Because `InMemoryRateLimiter` is process-local, global rate limiting across scaled Cloud Run instances should be enforced at the load balancer / Cloud Armor layer.
