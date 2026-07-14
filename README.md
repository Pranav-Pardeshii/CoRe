# CoRe (College Recommendation & Analytics Platform)

CoRe is a web application that helps engineering aspirants navigate Maharashtra's MHT-CET Centralized Admission Process (CAP). Instead of manually sifting through official cutoff PDFs, it provides instant, filterable college recommendations and historical cutoff trend analysis based on the last two years' actual CAP round data.

**Live Application:** [core-ui-733w.onrender.com](https://core-ui-733w.onrender.com)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Data Pipeline & Architecture](#data-pipeline--architecture)
  - [ETL Pipeline](#1-etl-pipeline-etl)
  - [Database Schema](#2-database-schema)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- **Granular college search** — filter eligible institutions by percentile, category, branch, and division
- **Historical trend analytics** — interactive cutoff-trend charts across years (2024–2025) and individual CAP rounds
- **Public access** — browsing and searching requires no login

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Pydantic v2 (data validation) |
| Auth | JWT (`python-jose`) — register/login endpoints exist; not currently required by any live feature |
| Database | MySQL (hosted on Aiven) |
| Frontend | Streamlit, Altair (data visualization) |
| Environment & package management | uv |

## Data Pipeline & Architecture

### 1. ETL Pipeline (`etl/`)

A multi-stage Python pipeline that ingests and normalizes raw data from official CAP round PDFs:

1. **Extraction** — pulls tabular data from multi-page PDFs into intermediate CSV structures
2. **Regional mapping** — decodes college codes to programmatically assign each institution to one of Maharashtra's 7 educational divisions
3. **Database ingestion** — normalizes and upserts the processed records into the relational schema below

### 2. Database Schema

Three tables, normalized around `branch_code`, with a composite unique constraint preventing duplicate cutoff rows:

```
colleges
├── college_code   VARCHAR(10)   PRIMARY KEY
├── college_name   VARCHAR(300)  NOT NULL
├── status         VARCHAR(300)
└── division       VARCHAR(100)

branches
├── branch_code    VARCHAR(15)   PRIMARY KEY
├── branch_name    VARCHAR(300)  NOT NULL
└── college_code   VARCHAR(10)   NOT NULL -> FK -> colleges.college_code

cutoffs
├── id             INT           PRIMARY KEY AUTO_INCREMENT
├── branch_code    VARCHAR(15)   NOT NULL -> FK -> branches.branch_code
├── year           SMALLINT      NOT NULL
├── round          TINYINT       NOT NULL
├── level          VARCHAR(10)   NOT NULL
├── stage          VARCHAR(5)    NOT NULL
├── category       VARCHAR(20)   NOT NULL
├── rank           INT           NOT NULL
└── percentile     FLOAT         NOT NULL

UNIQUE CONSTRAINT (branch_code, year, round, level, stage, category)
```

One row in `cutoffs` = one category's cutoff, for one branch, in one specific CAP round/year.

## Getting Started

### Prerequisites

Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/Pranav-Pardeshii/CoRe.git
cd CoRe
```

**2. Install dependencies**

```bash
uv sync
```

**3. Environment configuration**

Create a `.env` file inside `backend/` with your database credentials:

```env
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PORT=your-db-port
DB_PASS=your-db-password
DB_NAME=your-db-name
DB_SSL_CA=./backend/ca.pem
```

> If your database provider requires SSL, save the CA certificate at `backend/ca.pem`.

**4. Run it**

Start the FastAPI backend:

```bash
uv run uvicorn backend.main:app --reload
```

In a separate terminal, start the Streamlit frontend:

```bash
uv run streamlit run frontend/ui.py
```

## Roadmap

- [ ] **Saved shortlists** — wire the existing JWT auth into the frontend so logged-in users can save colleges to a personal list
- [ ] **Finer category filters** — split categories by gender, home-university allocation, and caste as separate selectable fields instead of one combined code
- [ ] **Pipeline automation** — a single-command CLI for ingesting future CAP round releases
- [ ] **More historical years** — pending normalization of older data formats (2023 and earlier don't yet match the current schema)

## License

This project is licensed under the [MIT License](LICENSE).
