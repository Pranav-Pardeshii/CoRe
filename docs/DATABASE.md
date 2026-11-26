# Database Schema & Alembic Migration Strategy

## Standardized Schema Overview

ORM models are defined in `backend/app/modules/*/models.py` with predictable constraint naming (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`) in `backend/app/infrastructure/database/base.py`:

| Legacy Table | Standardized Table | Key Column & Constraint Changes |
|---|---|---|
| `colleges` | `colleges` | Unchanged |
| `branches` | `branches` | Added `ix_branches_college_code` |
| `cutoffs` | `admission_cutoffs` | `year` -> `admission_year`, `round` -> `cap_round`, `stage` -> `admission_stage`, `rank` -> `merit_rank`; added `ck_admission_cutoffs_percentile_range`, `ix_admission_cutoffs_recommender`, `ix_admission_cutoffs_trends` |
| `users` | `users` | `password` -> `password_hash`; named `uq_users_username` |
| `saved_list` | `saved_list_items` | `rank` -> `sort_order`; added `fk_saved_list_items_branch_code_branches`, `ck_saved_list_items_sort_order_positive`, `ix_saved_list_items_user_sort_order` |

`saved_list_items` intentionally retains `college_code`, `college_name`, and `branch_name` alongside `branch_code` so `GET /saved-lists/` remains a single-table indexed read without joins.

> **Unverified live Aiven details**: Live Aiven MySQL (`mysql-core-core-v1.h.aivencloud.com:10944`) was unreachable from this environment (`socket.gaierror`), so exact production column lengths, index names, and constraint names on `users` and `saved_list` could not be inspected directly and must be verified before stamping production.

## Migration History

1. `0001_initial_schema`: Legacy-compatible baseline (`colleges`, `branches`, `cutoffs`, `users`, `saved_list`).
2. `0002_standardize_schema`: Renames `cutoffs` -> `admission_cutoffs`, `saved_list` -> `saved_list_items`, columns, check constraints, and query indexes.
3. `0003_password_hash_and_fk`: Renames `users.password` -> `password_hash` (preserving bcrypt hashes) and adds `fk_saved_list_items_branch_code_branches`.

## Exact Operational Order

### 1. Fresh Database Initialization
```powershell
uv run alembic -c backend/alembic.ini upgrade head
uv run python etl/loader.py
```

### 2. Existing Production Database Adoption
1. **Back up** the production Aiven database.
2. **Inspect & compare** live DDL (`SHOW CREATE TABLE` for all 5 tables) against `0001_initial_schema`.
3. **Stamp** the legacy baseline only after confirming schema parity:
   ```powershell
   uv run alembic -c backend/alembic.ini stamp 0001_initial_schema
   ```
4. **Run preflight orphan check** (read-only) before `0002`/`0003`:
   ```powershell
   uv run python -m backend.scripts.preflight_schema_check
   ```
5. **Upgrade** during a coordinated maintenance window with the updated backend and ETL:
   ```powershell
   uv run alembic -c backend/alembic.ini upgrade head
   ```

### 3. ETL Ingestion
`etl/loader.py` verifies `alembic_version`, `colleges`, `branches`, and `admission_cutoffs` exist before loading and refuses to run against an uninitialized database.
