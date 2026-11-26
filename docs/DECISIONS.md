# Architecture Decision Records (Summary)

1. **Async SQLAlchemy 2.x + `asyncmy` for FastAPI**:
   - Replaces import-time synchronous `mysql.connector` pooling with lifespan-managed `AsyncEngine` and per-request `AsyncSession`.
   - Keeps `mysql-connector-python` exclusively for the synchronous batch ETL pipeline (`etl/loader.py`).
2. **Feature-First Modular Monolith**:
   - Separates HTTP routers, Pydantic v2 schemas, service-level transaction boundaries, and SQLAlchemy repositories without over-engineering microservices.
3. **Custom JWT Auth Preserved**:
   - Retains `HS256`, 15-minute expiry, `sub` user ID claim, and `passlib[bcrypt]` hashes for full compatibility with existing accounts and Streamlit.
   - Fixes username enumeration (uniform `401` on login failure), payload dict mutation, and missing startup validation for `SECRET_KEY`.
4. **API Contract Stability**:
   - Preserves `/auth/*`, `/recommender/`, `/trends/`, `/saved-lists/`, `/`, and `/ping` paths and response shapes so `frontend/` works without immediate changes.
   - Aligns `/recommender/` `percentile` lower bound to `0` (`ge=0, le=100`) to match Streamlit's `0.0–100.0` input.
5. **Fail-Closed Test Safety**:
   - Integration tests read `CORE_TEST_DATABASE_URL` and fail closed unless the scheme is `mysql+asyncmy`, the host is loopback (or explicitly in `CORE_TEST_ALLOWED_HOSTS`), the database name is `core_test` or ends with `_test`, and `CORE_TEST_ALLOW_DESTRUCTIVE=1` is set.
6. **Process-Local Auth Rate Limiting**:
   - `InMemoryRateLimiter` uses bounded bucket pruning and `CORE_TRUSTED_PROXY_IPS` for `X-Forwarded-For` extraction. Because counters are process-local, multi-worker or multi-instance Cloud Run deployments require edge/load-balancer rate limiting for global enforcement.
