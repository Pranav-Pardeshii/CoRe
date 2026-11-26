# Product Requirements Document (PRD) — CoRe

## Overview

CoRe helps MHT-CET engineering aspirants in Maharashtra explore eligible colleges and branches based on their percentile, category, branch preference, and educational division, using historical CAP round cutoff data.

## Implemented Capabilities

1. **College Recommender (`GET /recommender/`)**:
   - Filters Stage I cutoffs across the latest 2 distinct admission years in MySQL (or `CORE_RECOMMENDER_YEARS`).
   - Supports `All` wildcard for `category`, `branch`, and `division`.
   - Evaluates eligibility via `MIN(percentile) <= user_percentile` per `(college_name, branch_name, branch_code)`.
   - Returns `min_cutoff`, `max_cutoff`, and total match count with single-query windowed pagination (`page >= 1`, `5 <= page_size <= 30`).
2. **Catalog Filters (`GET /catalog/filters`)**:
   - Returns distinct `categories`, `branches`, `divisions`, `years`, and `levels` queried from MySQL.
3. **Historical Cutoff Trends (`GET /trends/`)**:
   - Returns Stage I cutoff points `(year, round, level, percentile)` ordered by `(year, round, level)` for a `branch_code`, `category` (`All` maps to `GOPENS`), and optional `level`.
4. **User Accounts & Saved Shortlists (`POST /auth/*`, `/saved-lists/*`)**:
   - Username/password registration and OAuth2 password-flow login returning `HS256` JWTs (`Argon2id` password hashes).
   - Authenticated users can save up to 100 branches, view their ordered shortlist, bulk-reorder items, and delete items.
5. **ETL Batch Pipeline (`etl/`)**:
   - Single-pass `pdftotext -layout` extraction, leading-zero-preserving division mapping, fail-closed validation, and chunked `ON DUPLICATE KEY UPDATE` MySQL loading via `uv run python -m etl`.
6. **Streamlit Frontend (`frontend/`)**:
   - Dynamic filter loading via `CORE_API_BASE_URL`, `GOPENS` default category, multi-level Altair trend charts, centralized API client with `401` session cleanup, and saved-list management.
