# Architecture Decision Records (Summary)

1. **Async SQLAlchemy 2.x + `asyncmy` for FastAPI**:
   - Uses lifespan-managed `AsyncEngine` and per-request `AsyncSession`.
   - Keeps `mysql-connector-python` exclusively for the synchronous batch ETL package (`python -m etl`, in the `etl` dependency group).
2. **Feature-First Modular Monolith**:
   - Separates HTTP routers, Pydantic v2 schemas, service-level transaction boundaries, and SQLAlchemy repositories without over-engineering microservices.
3. **Argon2id (`pwdlib`) & PyJWT Auth**:
   - Uses `pwdlib[argon2]` (Argon2id) via `asyncio.to_thread` and `PyJWT[crypto]` (`HS256`, configurable expiry, `iat`/`iss`/`aud`/`type` claims).
   - Eliminates username enumeration with uniform `401` responses and precomputed dummy-hash verification, and enforces `>= 32`-char `CORE_SECRET_KEY` in production.
4. **Exact Decimal Precision & Dynamic Catalog**:
   - Stores `admission_cutoffs.percentile` as `DECIMAL(10, 7)` (`Numeric(10, 7)`) to avoid 32-bit float precision drift.
   - Queries `/recommender/` against the latest 2 distinct years present in MySQL (or `CORE_RECOMMENDER_YEARS`) and serves dynamic filter options via `GET /catalog/filters`.
5. **Fail-Closed Test Safety**:
   - Integration tests read `CORE_TEST_DATABASE_URL` and fail closed unless the scheme is `mysql+asyncmy`, the host is loopback (or explicitly in `CORE_TEST_ALLOWED_HOSTS`), the database name is `core_test` or ends with `_test`, and `CORE_TEST_ALLOW_DESTRUCTIVE=1` is set.
6. **Bounded Rate Limiting & Cloud Run Proxy Extraction**:
   - `InMemoryRateLimiter` uses an `OrderedDict` with O(1) LRU eviction, `CORE_TRUSTED_PROXY_IPS` (CIDR-aware), and `CORE_TRUSTED_PROXY_HOPS` (set to `1` behind Cloud Run GFE). Global multi-instance limits should be enforced at Cloud Armor.
7. **Google Cloud Production Target & Fresh Database Strategy (Option A)**:
   - Production target is **Google Cloud SQL for MySQL** (`CORE_DB_UNIX_SOCKET`), **Google Cloud Run** (`--workers 1`, `pool_size=2`, `max_overflow=3`), **Google Cloud Secret Manager**, **Artifact Registry**, and **GitHub Actions**.
   - Starting fresh on Cloud SQL: `alembic upgrade head` creates the schema from scratch (never `alembic stamp`), and `uv run python -m etl run` populates `colleges`, `branches`, and `admission_cutoffs`.
