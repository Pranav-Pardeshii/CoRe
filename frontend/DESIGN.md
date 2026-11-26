# DESIGN.md — CoRe Frontend Design System & Architecture

> **Aesthetic Thesis:** *Warm Editorial Precision* — a Swiss-Indian academic reference ledger crossed with a crisp modern examination gazette. Built for anxious Class 12 families on 4G Android phones and desktop side-by-side reviews.

---

## 1. Non-Negotiable Anti-Slop Rules

Every screen, component, and CSS rule in `frontend/` must strictly obey:
- **NO** `Inter`, `Roboto`, or generic system-SaaS default stacks.
- **NO** purple-to-blue gradients, mesh blobs, neon accents, or decorative hero illustrations.
- **NO** glassmorphism (`backdrop-filter: blur`), heavy drop shadows, or floating pill clouds.
- **NO** rounded-square icon tiles sitting above section headings.
- **NO** cards nested inside cards inside cards — use **hairline rules (`1px solid`)**, crisp typographic hierarchy, and subtle warm surface steps instead.
- **NO** marketing hero landing page blocking the Explorer tool.
- **NO** red/green-only status coding; every semantic margin state pairs hue + distinct luminance + text label + geometric glyph.

---

## 2. Color System (OKLCH, Light-First)

All colors are defined in **OKLCH** with perceptual contrast verified for bright outdoor mobile screens (`>= 4.5:1` for body text, `>= 3:1` for UI borders/graphics). No dark mode in v1 (paper-first daylight readability is prioritized; print styles inherit clean pure-white paper).

### Surfaces & Ink
| Token | OKLCH Value | Hex Fallback (approx.) | Role |
|---|---|---|---|
| `--bg-canvas` | `oklch(0.976 0.004 252)` | `#F5F6F9` | Archival mineral-slate paper background |
| `--bg-surface` | `oklch(1 0 0)` | `#FFFFFF` | Primary ledger sheet, filter bar, results rows, shortlist dock |
| `--bg-recessed` | `oklch(0.955 0.005 252)` | `#ECEEF3` | Input wells, table column headers, trend panel inset, secondary buttons |
| `--bg-hover` | `oklch(0.968 0.004 252)` | `#F2F4F8` | Row hover & subtle active surface |
| `--ink-primary` | `oklch(0.205 0.015 260)` | `#181A22` | Headlines, college names, cutoff numerals |
| `--ink-secondary` | `oklch(0.425 0.014 260)` | `#4D515E` | Branch names, category descriptions, helper text |
| `--ink-muted` | `oklch(0.545 0.012 260)` | `#6E7382` | Micro-labels, column captions, metadata |
| `--rule-subtle` | `oklch(0.892 0.006 252)` | `#DCDEE5` | Internal row dividers, hairline ledger rules |
| `--rule-strong` | `oklch(0.785 0.010 252)` | `#B8BCC8` | Input borders, panel frames, focus container edges |

### Single Authoritative Accent — Deep Gazette Indigo
| Token | OKLCH Value | Role |
|---|---|---|
| `--accent-primary` | `oklch(0.390 0.115 262)` | Primary CTA (`Find Colleges`), active tab indicator, selected priority badge, focus ring |
| `--accent-hover` | `oklch(0.330 0.118 262)` | Primary CTA hover/pressed |
| `--accent-tint` | `oklch(0.952 0.020 262)` | Subtle active filter pill, selected row highlight, saved badge background |
| `--accent-ink` | `oklch(0.990 0.004 85)` | Text on `--accent-primary` |

### Colorblind-Safe Semantic Cutoff Margins
Used strictly for comparing the student's entered percentile ($P$) against a branch's historical `[min_cutoff, max_cutoff]` range:

| State | Rule | Token (Ink) | Token (Tint) | Required Label & Marker |
|---|---|---|---|---|
| **Safe Margin** | $P \ge \text{max\_cutoff}$ | `oklch(0.410 0.095 178)` (Deep Spruce Teal) | `oklch(0.952 0.022 178)` | `● Safe margin` (`+X.XXXX` above max) |
| **Competitive** | $\text{min\_cutoff} + 0.5 \le P < \text{max\_cutoff}$ (or when $\text{min} = \text{max}$ edge) | `oklch(0.500 0.115 74)` (Warm Ochre) | `oklch(0.958 0.028 82)` | `◐ In range` (within historical spread) |
| **Borderline** | $\text{min\_cutoff} \le P < \text{min\_cutoff} + 0.5$ | `oklch(0.470 0.125 34)` (Muted Terracotta) | `oklch(0.954 0.024 36)` | `△ Borderline` (close to historical floor) |
| **Status / Alert** | Error banners | `oklch(0.450 0.145 25)` | `oklch(0.956 0.024 25)` | Calm inline notice with retry action |

### Trend Series Palette (Multi-Year Separation)
When plotting 2–3 years inside a single selected Seat Level (`SL`, `HU_HU`, etc.):
- **Latest Year (e.g., 2025):** `--accent-primary` (`oklch(0.390 0.115 262)`), solid `2.25px` stroke, filled circle nodes.
- **Previous Year (e.g., 2024):** `oklch(0.520 0.110 42)` (Warm Burnt Sienna), dashed `2px` (`5 4`) stroke, hollow/square nodes.
- **Earlier Year (if present):** `oklch(0.470 0.080 178)` (Teal-Slate), dotted `2px` stroke, diamond nodes.
- **Student Percentile Reference Line:** Horizontal `1px` dashed rule in `oklch(0.350 0.015 260)` labeled `Your score: XX.XXXXXXX`.

---

## 3. Typography & Numeric Precision

### Font Stack
Self-hosted or bundled cleanly via `@fontsource` (zero layout shift, fast offline/4G cache):
1. **Editorial Masthead (`--font-display`):** `'Newsreader', Georgia, serif`
   - Used *sparingly* for the compact **CoRe** masthead title, print-view sheet header, and empty-state headings. Never used for dense table cells or buttons.
2. **UI & Body (`--font-sans`):** `'IBM Plex Sans', system-ui, -apple-system, sans-serif`
   - Crisp, humanist-technical legibility for long Maharashtra college names (`Veermata Jijabai Technological Institute (VJTI), Matunga, Mumbai`), branch names, and decoded category labels.
3. **Numeric & Code (`--font-mono`):** `'IBM Plex Mono', ui-monospace, monospace`
   - Enforced with `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;` on **every**:
     - Percentile input & cutoff readout (`99.4821500`)
     - Branch / DTE code (`0100219110`)
     - CAP round badge (`R1`, `R2`, `R3`, `R4`)
     - Option Form priority index (`01`, `02`, …, `100`)
     - Result counts & pagination indicators (`1–20 of 148`)

### Type Scale (Fluid & Tight)
| Role | Family | Size | Weight | Line Height | Tracking |
|---|---|---|---|---|---|
| Masthead Wordmark | `--font-display` | `1.375rem` (22px) | `600` | `1.15` | `-0.015em` |
| Section Header | `--font-sans` | `0.9375rem` (15px) | `600` | `1.3` | `-0.01em` |
| College Name (Row) | `--font-sans` | `0.96875rem` (15.5px) | `600` | `1.32` | `-0.008em` |
| Branch / Secondary | `--font-sans` | `0.84375rem` (13.5px) | `400` | `1.4` | `0` |
| Micro Label / Column Head | `--font-sans` | `0.71875rem` (11.5px) | `600` | `1.2` | `0.04em` (uppercase) |
| Cutoff Numeral (Table/Row) | `--font-mono` | `0.875rem` (14px) | `500` | `1.2` | `-0.01em` |
| Percentile Hero Input | `--font-mono` | `1.125rem` (18px) | `600` | `1.2` | `-0.015em` |

---

## 4. Layout, Spacing & Responsive Architecture

### Spatial Philosophy
- **Max Container Width:** `1320px` centered, `16px` horizontal gutter on mobile (`< 640px`), `24px` on tablet/desktop.
- **Border Radius Discipline:** Sharp editorial corners — `6px` for outer ledger panels/inputs, `4px` for buttons and badges, `9999px` only for tiny status dots/segmented pills. Zero `16px–24px` bubbly SaaS cards.
- **Elevation Discipline:** Zero drop shadows on resting elements (`box-shadow: none`). Structural hierarchy uses `1px solid var(--rule-subtle)` and background contrast (`--bg-canvas` vs `--bg-surface`). Shadows are reserved strictly for mobile bottom sheets or popovers (`0 8px 24px oklch(0.2 0.02 260 / 0.10)`).

### Breakpoints & Workspace Geometry

#### 1. Compact Header Bar (`52px` height, full width)
- **Left:** `CoRe` masthead mark + concise subtitle tag (`MHT-CET CAP Explorer`).
- **Right:**
  - Mobile-only Option Form pill button (`Option Form · 04`) jumping/toggling to the shortlist sheet.
  - Account control (`Sign in` / `@username · Sign out`) opening a clean inline modal/popover (no sidebar clutter).

#### 2. Query Strip (Pinned / Top of Workspace, zero hero bloat)
- Sits immediately under the header as a single high-clarity hairline-framed band (`--bg-surface`, `1px solid var(--rule-strong)`):
  - **Percentile Input** (prominent, `inputMode="decimal"`, placeholder `e.g. 98.5432100`, inline validation `0–100`, up to 7 decimals).
  - **Seat Category Combobox** (searchable dropdown showing `CODE` in `--font-mono` + decoded label in `--font-sans`; defaults to `GOPENS`).
  - **Branch Combobox** (searchable, defaults to `All Branches`).
  - **Division Select** (defaults to `All Divisions`).
  - **Primary Action (`Find Colleges`)** — full-width on `< 640px`, inline right-aligned on desktop (`min-height: 44px` for thumb ergonomics).
- On mobile (`< 768px`), after results load, optional `Branch` & `Division` filters can collapse behind a `Filters (Active: 1)` toggle if the user taps to inspect more rows, keeping `Percentile` + `Category` always one tap away.

#### 3. Main Dual-Column Workspace (`>= 1024px`) vs Tabbed/Sheet (`< 1024px`)
- **Desktop (`>= 1024px`):** CSS Grid `minmax(0, 1fr) 360px` with `24px` gap.
  - **Left Column (Explorer Ledger):**
    - Results Summary Bar: `148 eligible choices · Ordered by highest historical cutoff` + Page-size selector (`10` / `20` / `30`) + Active category badge.
    - **Desktop Table / Structured Ledger:** Clean hairline rows (no nested cards!) displaying:
      1. College & Branch (`college` + `branch` + `branch_code` pill)
      2. Historical Cutoff Range (`min_cutoff` – `max_cutoff` in 7-decimal `IBM Plex Mono`)
      3. Margin Badge (`Safe margin` / `In range` / `Borderline`)
      4. Actions (`Trends` toggle button + `+ Shortlist` / `✓ Shortlisted (#3)`)
    - **Inline Expandable Trend Drawer:** Clicking `Trends` expands a single full-width hairline-inset panel (`--bg-recessed`) directly beneath that row—never a cramped mini-chart inside a narrow column, and never a full-page navigation that loses scroll position!
    - **Pagination Footer:** `Previous`, `Page X of Y`, `Next` with `44px` hit targets.
  - **Right Column (Sticky CAP Option Form Dock, `position: sticky; top: 16px`):**
    - Header: `CAP Option Form` + counter (`12 / 100`) + sync status (`Saved to account` or `Draft on this device · Sign in to sync`).
    - Ordered List: Priority `#01`, `#02`… with College Name, Branch Name, quick controls (`↑`, `↓`, `Move to #`, `Remove`).
    - Footer Actions: **Print Form** (triggers clean print stylesheet) + **Export CSV** / **Copy List**.
- **Mobile (`< 1024px`):**
  - Single-column stacked ledger rows (`padding: 14px 16px`, `1px solid var(--rule-subtle)` dividers).
  - Each mobile row keeps a crisp 3-line scan order:
    - Line 1: **College Name**
    - Line 2: **Branch Name** · `0100219110`
    - Line 3: `Min 88.5013511` — `Max 92.1400200` + Margin pill
    - Line 4: Two `40px+` touch buttons (`Cutoff Trends` | `+ Add to Form` / `In Form #03`)
  - **Option Form Access:** Bottom sticky bar or top segmented switch (`Explorer` | `Option Form (N)`) so switching between browsing and reordering never requires scrolling back up.

---

## 5. Key Component Specifications

### A. 7-Decimal Percentile Input
- **Element:** `<input type="text" inputMode="decimal" autoComplete="off" />`
- **Behavior:**
  - Strips invalid non-digit/non-dot characters; allows at most one decimal point and up to 7 fractional digits.
  - Rejects values `< 0` or `> 100` with calm inline hint: *"Enter a percentile between 0 and 100 (up to 7 decimal places)."*
  - Preserves exact string while typing (`"99.4800000"`) and sends numeric `percentile` query param with full precision.

### B. Searchable Category Combobox (104+ Codes)
- **Trigger:** Displays current selection cleanly: `[GOPENS]` (mono pill) + `General, Open, State Level`.
- **Dropdown / Mobile Sheet:**
  - Instant client-side filter matching either code (`LOBCH`) or plain-English words (`Ladies`, `OBC`, `Home University`, `TFWS`, `Defence`).
  - Groups or prioritizes common categories at top (`GOPENS`, `GOPENH`, `GOBCS`, `GOBCH`, `LOPENH`, `TFWS`, `EWS`) while keeping full alphabetical access to all codes returned by `/catalog/filters`.
  - Selecting `All` renders an amber-ochre advisory note explaining that `All` mixes General, Reserved, Defence, PWD, and Orphan cutoffs.

### C. Seat-Level-Separated Cutoff Trend Chart
- **Technology:** Lightweight custom **SVG chart** (zero heavy charting library bundle like Vega/Altair/Recharts—critical for mid-range Android 4G performance!).
- **Anatomy:**
  - **Seat Level Segmented Tabs** at top of the expanded panel (`State Level (SL)` | `Home Univ -> Home Univ (HU_HU)` | `Other -> Home Univ (OHU_HU)` etc., showing only levels present in `/trends/` response).
  - **SVG Line Plot (`height: 200px`, responsive `viewBox`):**
    - X-axis: `R1`, `R2`, `R3`, `R4` (only rounds present or `R1–R4` fixed ticks).
    - Y-axis: `tabular-nums` percentile ticks auto-bounded to `[min - 0.5, max + 0.5]` clamped to `[0, 100]`.
    - Interactive tap/hover point inspection showing exact `(Year, Round, Percentile)` without fragile tiny hitboxes (generous invisible `<circle r="18">` tap targets for fingers!).
  - **Compact Numerical Ledger Table** right below the SVG listing `Year | Round | Cutoff Percentile` so every exact 7-decimal digit is readable at a glance and screen-reader accessible.

### D. CAP Option Form Reorder & Print System
- **Reordering UX for up to 100 items:**
  - Up/Down buttons for 1-step tweaks (`min-width: 36px; min-height: 36px`).
  - Tap priority number badge (`#14`) -> inline small input (`Move to position: [ 3 ]`) so moving item #42 to #3 on a phone takes 2 taps instead of 39 taps!
  - Drag handle (`⋮⋮`) on desktop pointer devices via accessible drag-and-drop / keyboard `Space` + Arrow keys.
- **Print Stylesheet (`@media print`):**
  - Hides header controls, query strip, explorer rows, and action buttons.
  - Renders an A4 black-on-white **MHT-CET CAP Option Form Checklist** with student profile summary (Percentile, Category, Date printed) and clean numbered table (`Pref #`, `College Name`, `Branch Name`, `Branch Code` if available, `Notes / DTE Check`).

---

## 6. Performance & Accessibility Guardrails (80%+ Mobile 4G Target)

1. **Bundle Budget:** Prefer lightweight React + TypeScript + Vite with custom SVG trend charts and zero heavy UI/chart frameworks (target initial JS `< 90 KB` gzipped).
2. **Request Hygiene:**
   - Cache `/catalog/filters` in memory + `sessionStorage` for the session (matching backend `max-age=3600` cache header).
   - Cancel in-flight `/recommender/` and `/trends/` requests via `AbortController` when filters change rapidly.
   - Cache `/trends/` responses per `(branch_code, category)` in session memory to eliminate duplicate network fetches when toggling rows.
3. **Accessibility (`WCAG 2.1 AA`):**
   - Minimum `44×44px` touch targets on primary mobile controls; `>= 36×36px` with generous spacing on dense reorder icons.
   - `aria-live="polite"` announcements for result counts (`"148 eligible colleges loaded"`), shortlist additions, and error states.
   - Keyboard-navigable comboboxes, expandable trend panels (`aria-expanded`), and accessible reorder controls.
4. **Strict Copy Compliance:** Every error adapter maps network failures, HTTP status codes, and malformed payloads to plain admissions English—never exposing backend stack names or raw HTTP status numbers.
