# Product Requirements Document (PRD) — CoRe

## Overview

CoRe helps MHT-CET engineering aspirants in Maharashtra explore eligible colleges and branches based on their percentile, category, branch preference, and educational division, using historical CAP round cutoff data (2024–2025).

## Implemented Capabilities

1. **College Recommender**:
   - Filters Stage I cutoffs for years `2024` and `2025`.
   - Supports `All` wildcard for `category`, `branch`, and `division`.
   - Evaluates eligibility via `MIN(percentile) <= user_percentile` per `(college_name, branch_name, branch_code)`.
   - Returns `min_cutoff`, `max_cutoff`, and total match count with pagination (`page >= 1`, `5 <= page_size <= 30`).
2. **Historical Cutoff Trends**:
   - Returns Stage I cutoff points `(year, round, percentile)` ordered by `(year, round)` for a `branch_code` and `category` (`All` maps to `GOPENS`).
3. **User Accounts & Saved Shortlists**:
   - Username/password registration and OAuth2 password-flow login returning 15-minute `HS256` JWTs.
   - Authenticated users can save branches, view their ordered shortlist, reorder items, and delete items.
4. **ETL Batch Pipeline (`etl/`)**:
   - Extracts CAP round PDFs into CSVs, maps college codes to Maharashtra divisions, and loads normalized `colleges`, `branches`, and `cutoffs` rows into MySQL.
5. **Streamlit Frontend (`frontend/`)**:
   - Interactive search UI, Altair trend charts, sidebar login/register, and saved-list management.
