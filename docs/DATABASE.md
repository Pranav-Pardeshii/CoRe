# Database Schema & Alembic Migration Strategy

## Standardized Schema Overview

ORM models are defined in `backend/app/modules/*/models.py` with predictable constraint naming (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`) in `backend/app/infrastructure/database/base.py`:

| Legacy Table | Standardized Table | Key Column Changes |
|---|---|---|
| `colleges` | `colleges` | Unchanged |
| `branches` | `branches` | Added `ix_branches_college_code` |
| `cutoffs` | `admission_cutoffs` | `year` -> `admission_year`, `round` -> `cap_round`, `stage` -> `admission_stage`, `rank` -> `merit_rank`; added `ck_admission_cutoffs_percentile_range`, `ix_admission_cutoffs_recommender`, `ix_admission_cutoffs_trends` |
| `users` | `users` | Named `uq_users_username` |
| `saved_list` | `saved_list_items` | `rank` -> `sort_order`; added `ck_saved_list_items_sort_order_positive`, `ix_saved_list_items_user_sort_order` |

> **Unverified live Aiven details**: Live Aiven MySQL (`mysql-core-core-v1.h.aivencloud.com:10944`) was unreachable from this environment (`socket.gaierror`), so exact production column lengths, index names, and constraint names on `users` and `saved_list` could not be inspected directly and must be verified before stamping production.

## Migration History

1. `0001_initial_schema`: Legacy-compatible baseline matching `colleges`, `branches`, `cutoffs`, `users`, `saved_list`.
2. `0002_standardize_schema`: Forward migration renaming `cutoffs` -> `admission_cutoffs` and `saved_list` -> `saved_list_items`, renaming columns, and adding check constraints and query indexes without data loss.

## Adopting an Existing Production Database into Alembic

1. **Back up** the production Aiven database before any migration command.
2. **Inspect & compare** the live schema (`SHOW CREATE TABLE` for all 5 tables) against `0001_initial_schema`.
3. **Stamp** the legacy baseline only after verifying the schema matches:
   ```powershell
   uv run alembic -c backend/alembic.ini stamp 0001_initial_schema
   ```
4. **Upgrade** to `0002_standardize_schema` in a maintenance window (with the updated backend + ETL deployed together):
   ```powershell
   uv run alembic -c backend/alembic.ini upgrade head
   ```
5. **ETL Note**: `etl/loader.py` targets `admission_cutoffs` and still retains `CREATE TABLE IF NOT EXISTS` as a transitional guard until Alembic is stamped on all environments.
