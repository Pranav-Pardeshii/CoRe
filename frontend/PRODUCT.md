# PRODUCT.md — CoRe (College Recommendation & CAP Option Form Planner)

> **Scope:** Product specification for the CoRe web frontend (`frontend/`), replacing the legacy Streamlit prototype while preserving 100% compatibility with the FastAPI backend contracts documented in [`docs/API.md`](../docs/API.md).

---

## 1. Product Identity & Mission

**CoRe** is an MHT-CET Engineering College Explorer and CAP (Centralized Admission Process) Option Form Planner built for Class 12 engineering aspirants and their parents across Maharashtra.

During MHT-CET CAP results week, students make high-stakes preference decisions using official cutoff lists spanning hundreds of colleges, branches, seat categories, and multi-round allocations. Existing PDFs and generic predictor portals force families to decode cryptic CET seat codes (`GOPENS`, `LOBCH`, `DEFRNT1S`), squint at rounded percentiles, and manually track preferences in spreadsheets.

CoRe turns official historical Stage I CAP cutoff records into a calm, fast, trustworthy decision instrument:
1. **Immediate eligibility lookup** down to 7 decimal places of MHT-CET percentile.
2. **Plain-English seat category decoding** alongside official CAP codes.
3. **Clean historical trend inspection** across admission years, CAP rounds (`R1`–`R4`), and seat allocation levels (`SL`, `HU_HU`, `HU_OHU`, `OHU_HU`, `OHU_OHU`).
4. **Ordered CAP Option Form planning** with effortless priority reordering, export, and print-ready formatting.

---

## 2. Target Users & Operating Context

| Dimension | Reality & Design Implication |
|---|---|
| **Primary Users** | Class 12 MHT-CET engineering aspirants (ages 17–19) and their parents reviewing choices together. |
| **Device Split** | **80%+ mobile traffic** on mid-range Android smartphones over 4G/5G connections; **~20% desktop/laptop** used for side-by-side family comparison and printing Option Forms. |
| **Emotional State** | High-stakes, time-pressured, anxious during CAP Round 1–4 windows. Zero patience for marketing fluff, slow hydration, or cryptic errors. |
| **Core Success Metric** | Time from page load to seeing accurate eligible colleges and opening a trend or adding to the Option Form (< 5 seconds on 4G). |
| **Entry Point** | Opens **directly into the live Percentile & Category Explorer**. No hero banner, no feature carousel, no login wall. |

---

## 3. Core User Jobs & Flows

### Job 1 — Check Eligible Colleges & Branches
- **Inputs:**
  - **MHT-CET Percentile (`0.0000000` – `100.0000000`):** Accepts up to 7 decimal places (e.g., `99.4821500`). Uses decimal keypad on mobile (`inputMode="decimal"`), preserves trailing zeros and full precision, and never forces integer/2-decimal rounding.
  - **Seat Category:** Searchable selector displaying decoded plain-English meaning alongside the official CAP code (e.g., `GOPENS — General, Open, State Level`). Defaults to `GOPENS` (if present in `/catalog/filters`, else first non-`All` or `All`). Selecting `All` displays a clear inline advisory: *"Showing all seat types combined (General, Reserved, Defence, PWD, and Orphan). Pick your exact category for accurate eligibility."*
  - **Preferred Branch (optional):** Defaults to `All`; searchable list from `/catalog/filters`.
  - **Maharashtra Division (optional):** Defaults to `All`; lists divisions from `/catalog/filters` (`Amravati Division`, `Aurangabad Division`, `Mumbai Division`, `Nagpur Division`, `Nashik Division`, `Pune Division`).
- **Execution:** `GET /recommender/` with `page` (`>= 1`) and `page_size` (`5`–`30`, default `10` on mobile / `20` on desktop or user-selectable `10 / 20 / 30` within backend `5..30`).
- **Output & Ranking:**
  - Displays total matching choices (`count`) and results ordered by `max_cutoff DESC, branch_code ASC` (matching backend ordering).
  - Each row/item shows: **College Name**, **Branch Name**, **Branch Code** (`tabular-nums`), **Min Cutoff** & **Max Cutoff** (7 decimal places), and a calm **Margin Indicator** comparing the student's entered percentile against `[min_cutoff, max_cutoff]` across the latest admission years (`Safe Margin`, `Competitive Range`, `Borderline`).
  - Zero-result state guides action calmly without dead ends (suggesting widening branch/division to `All` or adjusting category/percentile).

### Job 2 — Inspect Multi-Year CAP Round Cutoff Trends
- **Trigger:** Expanding or selecting **"Cutoff Trends"** on any eligible college-branch row (or from a saved item when `branch_code` is known).
- **Data Source:** `GET /trends/?branch_code=...&category=...` (`All` category automatically maps on backend to `GOPENS`; UI explicitly tells the user when `GOPENS` is shown for `All`).
- **Visualization Requirements:**
  - Shows **CAP Rounds (`R1`, `R2`, `R3`, `R4`)** on the horizontal axis and **Cutoff Percentile** on the vertical axis (tightly scaled around the branch's min/max with padding, never wasted 0–100 scale).
  - **Clean separation by Seat Level:** Data contains distinct seat-allocation levels (`SL` = State Level, `HU_HU` = Home University seat for Home University candidate, `HU_OHU`, `OHU_HU`, `OHU_OHU`). Trends **must never tangle incompatible seat levels into a single ambiguous line**—provide explicit seat-level segmentation (filter tabs/pills per available level, defaulting to `SL` or the first available level, with multi-year series e.g. `2024` vs `2025` cleanly distinguished by color + dash/marker).
  - Include a compact **exact-value reference table** alongside/below the chart so mobile users and parents can read exact 7-decimal numbers without hovering.

### Job 3 — Build, Reorder & Export the CAP Option Form Shortlist
- **Capacity:** Up to **100** college-branch choices (enforced by backend `MAX_SAVED_LIST_ITEMS = 100`).
- **Two-Tier Frictionless Shortlisting (Resolved Decision):**
  - **Guest / Instant Draft Mode:** Unauthenticated visitors can still shortlist, reorder, print, and export a **Local Draft Option Form** persisted in `localStorage` so they never hit an account wall while comparing options with parents.
  - **Account-Synced Mode:** Signing in (`POST /auth/login`) or creating an account (`POST /auth/register`) syncs their shortlist with `/saved-lists/` (`GET`, `POST`, `PUT`, `DELETE`).
  - **Auth Rules:** Username (`3–50` chars, letters, digits, `.`, `_`, `-`) and password (`8–128` chars) validated inline before submission. When a signed-in user has local draft items created before login, offer a one-click **"Import local draft to account"** action (respecting the 100-item cap) rather than silently overwriting either list.
- **Reordering & Management:**
  - Clear numbered priority (`01`, `02`, `03`...) matching CAP Option Form submission order.
  - **Accessible multi-modal reordering:** Touch-friendly `Move Up` / `Move Down` buttons, **Move to Position #N** quick jump (essential when managing 30–100 choices on a phone), and drag-and-drop on pointer devices, all submitting `PUT /saved-lists/` with `{ ordered_list: [id, ...] }` (deduplicated, exact owned ID set).
  - Remove choice (`DELETE /saved-lists/{id}`) with immediate UI feedback and undo/restore option where appropriate.
- **Print & Export (Critical CAP Workflow):**
  - **Print Option Form (`@media print`):** Dedicated A4 clean ledger print layout stripping navigation/filters and printing numbered priority (`#`), College Name, Branch Name (and Branch Code when available), plus date/percentile/category header for filling the official CET Cell CAP form.
  - **Export CSV / Copy List:** One-tap CSV download or plain-text copy of the ordered preference list for offline sharing over WhatsApp with parents/mentors.

---

## 4. Domain Rules & Data Realities

1. **CAP Category Decoding:**
   - The catalog contains ~104 distinct CAP category codes (e.g., `GOPENS`, `LOBCH`, `GNT1H`, `PWDROBCS`, `DEFRSEBC`, `DEFRNT1SS`, `TFWS`, `EWS`, `ORPHAN`, `MI`).
   - Every category selector and badge must display `CODE — Plain English Meaning` (e.g., `LOBCH — Ladies-only, OBC, Home University`).
   - The TypeScript decoder must port [`frontend/category_labels.py`](category_labels.py) and handle known edge patterns in the dataset (e.g., `DEFRSEBC` without a trailing `S`/`H`/`O` suffix, `DEFRNT1SS` double-suffix variants) without falling back to raw unparsed strings whenever components are recognizable.
2. **Seat Level Decoding:**
   - `SL`: State Level
   - `HU_HU`: Home University Candidate — Home University Seat
   - `HU_OHU`: Home University Candidate — Other than Home University Seat
   - `OHU_HU`: Other than Home University Candidate — Home University Seat
   - `OHU_OHU`: Other than Home University Candidate — Other than Home University Seat
3. **Backend Contract Constraints (No Backend Changes Assumed):**
   - `GET /catalog/filters` -> `{ categories, branches, divisions, years, levels }` (`Cache-Control: public, max-age=3600`).
   - `GET /recommender/` -> `{ eligible_colleges: [{ college, branch, branch_code, min_cutoff, max_cutoff }], count }`. Note: does not return `division` or college `status` per row; queries Stage I cutoffs across the latest 2 distinct years.
   - `GET /trends/` -> `{ branch_code, count, trends: [{ year, round, level, percentile }] }`.
   - `GET /saved-lists/` -> `{ saved_list: [{ id, college_name, branch_name }] }`. Note: `branch_code` is not returned by `GET /saved-lists/`, so client caches `branch_code` metadata locally when known and omits it cleanly when unavailable (e.g., in print/export).
   - `POST /auth/login` uses `application/x-www-form-urlencoded` (`username`, `password`); `POST /auth/register` uses JSON (`{ username, password }`).
   - CORS: Backend `CORE_CORS_ORIGINS` must include the React dev/production origin during integration.

---

## 5. Voice, Copy & Error Translation Rules

### Tone
- **Calm, factual, encouraging, plain Indian English** tailored to Maharashtra engineering admissions.
- Concise labels; zero slang, zero exclamation spam (`"Bingo!"` from backend messages must never be surfaced directly in the UI).

### Hard Ban on Technical Jargon
**Never display any of the following words or codes anywhere in user-facing UI, tooltips, or error banners:**
`FastAPI`, `API`, `backend`, `server`, `MySQL`, `database`, `JWT`, `token`, `endpoint`, `Cloud Run`, `SQL`, `JSON`, `401`, `404`, `409`, `422`, `429`, `500`, `503`.

### Error & Status Copy Mapping

| Situation | Forbidden Raw Message | Required User-Facing Copy |
|---|---|---|
| Network failure / backend unreachable | `Could not reach the server` / `Failed to fetch` | *"Couldn't connect right now. Check your internet and try again."* |
| Initial filter load failure | `Unable to load filter options from the backend` | *"Couldn't load college categories and branches right now. Please retry."* |
| Recommender request error (`500` / non-JSON) | `Server returned HTTP 500` / `Internal server error` | *"Couldn't load matching colleges right now. Please try again in a moment."* |
| Trends load failure | `Couldn't load trend: ...` | *"Couldn't load cutoff history for this branch right now."* |
| Trends empty (`count === 0`) | `No rows` | *"Not enough past CAP round data to show a trend for this category."* |
| Invalid login (`401` on `/auth/login`) | `401 Unauthorized` | *"That username or password didn't match. Please check and try again."* |
| Expired session (`401` on authenticated calls) | `JWT expired` / `401` | *"Your session timed out. Sign in again to view and sync your saved Option Form."* |
| Rate limited (`429`) | `429 Too Many Requests` | *"Too many attempts in a short time. Please wait a minute and try again."* |
| Duplicate username (`409` on register) | `409 Conflict` | *"That username is already taken. Try adding a number or choosing another."* |
| Duplicate saved item (`409` on `/saved-lists/`) | `409` / `You already saved this Item` | *"This college and branch is already in your Option Form."* |
| Saved list 100-item limit (`400`) | `HTTP 400` | *"Your Option Form has reached the 100-choice limit. Remove an option to add another."* |
| Stale reorder state (`400` / `404`) | `Invalid Input!` / `Item not found!` | *"Your saved list changed elsewhere. Refreshing your latest Option Form…"* |

---

## 6. Resolved Product Decisions

1. **Immediate Explorer Landing:** No marketing splash screen. The Explorer workspace is the root route (`/`).
2. **Guest Draft + Optional Account Sync:** Students can build, reorder, print, and export a Local Draft Option Form immediately without registering; signing in enables cross-device persistence via `/saved-lists/` with optional draft import.
3. **Full 7-Decimal Precision Everywhere:** Percentiles are entered via `inputMode="decimal"` (accepting up to 7 decimal places without forced rounding) and displayed consistently to 7 decimal places (`tabular-nums`) so `0.0001` differences remain visible.
4. **Pagination Control:** Default `page_size=10` on mobile and `20` on desktop (user-selectable `10`, `20`, or `30`, staying strictly within backend `5 <= page_size <= 30`).
5. **No Backend Assumptions Beyond Existing Endpoints:** All features work solely against `/catalog/filters`, `/recommender/`, `/trends/`, `/auth/*`, and `/saved-lists/` without requiring backend schema changes.
