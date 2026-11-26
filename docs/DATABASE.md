# Database Schema & Alembic Migration Strategy

## Standardized Schema Overview

ORM models are defined in `backend/app/modules/*/models.py` with predictable constraint naming (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`) in `backend/app/infrastructure/database/base.py`:

| Table | Key Columns & Constraints |
|---|---|
| `colleges` | `college_code` (`VARCHAR(10)` PK), `college_name`, `status`, `division`, `ix_colleges_division` |
| `branches` | `branch_code` (`VARCHAR(15)` PK), `branch_name`, `college_code` FK, `ix_branches_college_code`, `ix_branches_branch_name_college_code` |
| `admission_cutoffs` | `id` PK, `branch_code` FK, `admission_year`, `cap_round`, `level`, `admission_stage`, `category`, `merit_rank`, `percentile` (`DECIMAL(10, 7)`), `created_at`; `uq_admission_cutoffs_composite`, `ck_admission_cutoffs_percentile_range`, `ix_admission_cutoffs_recommender`, `ix_admission_cutoffs_stage_year_branch`, `ix_admission_cutoffs_trends` |
| `users` | `id` PK, `username` (`uq_users_username`), `password_hash`, `created_at`, `updated_at` |
| `saved_list_items` | `id` PK, `user_id` FK (`ON DELETE CASCADE`), `college_code`, `branch_code` FK (`fk_saved_list_items_branch_code_branches`), `college_name`, `branch_name`, `sort_order`, `created_at`, `updated_at`; `uq_saved_list_items_user_branch`, `ck_saved_list_items_sort_order_positive`, `ix_saved_list_items_user_sort_order` |

`saved_list_items` intentionally retains `college_code`, `college_name`, and `branch_name` alongside `branch_code` so `GET /saved-lists/` remains a single-table indexed read without joins.

## Migration History

1. `0001_initial_schema`: Initial baseline (`colleges`, `branches`, `cutoffs`, `users`, `saved_list`).
2. `0002_standardize_schema`: Renames `cutoffs` -> `admission_cutoffs`, `saved_list` -> `saved_list_items`, columns, check constraints, and query indexes.
3. `0003_password_hash_and_fk`: Renames `users.password` -> `password_hash` and adds `fk_saved_list_items_branch_code_branches`.
4. `0004_production_hardening`: Converts `percentile` to `DECIMAL(10, 7)`, aligns `uq_users_username`, adds covering/lookup indexes, and adds `created_at`/`updated_at` timestamps.

## Fresh Cloud SQL Initialization Plan (Option A)

1. **Provision empty database** on Google Cloud SQL for MySQL 8.0 and configure credentials securely (Secret Manager / Cloud SQL Auth Proxy or Unix socket).
2. **Initialize schema** (do **not** use `alembic stamp` on a fresh database):
   ```powershell
   uv run alembic -c backend/alembic.ini upgrade head
   ```
3. **Verify schema**: Run `uv run alembic -c backend/alembic.ini check` to confirm zero drift.
4. **Ingest catalog & cutoff data**: Ensure the gitignored source PDFs (`PDFs/`) are present locally, then run:
   ```powershell
   uv run python -m etl run --pdf-dir PDFs --output-dir csvs --csv-path cutoffs_flat.csv
   ```
   `etl` validates all rows fail-closed, verifies `alembic_version`, `colleges`, `branches`, and `admission_cutoffs` exist, and upserts in 2,000-row chunks via `ON DUPLICATE KEY UPDATE`.
5. **Verify counts & endpoints**: Check post-load row counts logged by `etl`, then smoke-test `/health/live`, `/health/ready`, `/catalog/filters`, `/auth/register`, `/auth/login`, `/recommender/`, `/trends/`, and `/saved-lists/`.
