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
   - Integration tests read `CORE_TEST_DATABASE_URL` and fail closed if the scheme is not `mysql+asyncmy`, the host looks like production/Aiven, or the database name does not contain `test`.
