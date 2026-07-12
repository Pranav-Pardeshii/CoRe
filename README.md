# CoRe (College Recommendation & Analytics Platform)

CoRe is a high-performance web application designed to help engineering aspirants navigate the complexities of the Maharashtra MHT-CET Centralized Admission Process (CAP). The platform eliminates the need to manually sift through massive, unstructured official cutoff PDFs by providing instant, filterable college recommendations and historical cutoff trend analysis.

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

- **Granular College Search** — Filter eligible institutions instantly by percentile, category, specific engineering branches, and geographic divisions.
- **Historical Trend Analytics** — Dynamic, interactive visualization of cutoff fluctuations across multiple years (2024–2025) and individual CAP rounds.
- **Public Access Layer** — Public-facing, high-throughput browsing enabled with zero login friction.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Async REST API), Pydantic v2 (Data Validation) |
| Database | MySQL (Hosted on Aiven) |
| Frontend | Streamlit, Altair (Data Visualization) |
| Environment & Package Management | uv |

## Data Pipeline & Architecture

### 1. ETL Pipeline (`etl/`)

The core value engine of CoRe is a modular multi-stage Python ETL pipeline designed to ingest and normalize raw data from state-issued CAP round PDFs:

1. **Extraction** — Extracts erratic, tabular data from multi-page PDFs into standardized intermediate CSV structures.
2. **Feature Engineering (Regional Mapping)** — Decodes institutional college codes to programmatically determine and inject geographic data, categorizing institutions across Maharashtra's 7 primary educational divisions based on code prefixes.
3. **Database Ingestion** — Normalizes and upserts the processed records into the relational schema.

### 2. Database Schema

The database is architected around a 3-tier normalized layout optimized for fast analytical lookups, maintaining data integrity via a robust composite unique constraint.

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
├── rank            INT           NOT NULL
└── percentile     FLOAT         NOT NULL

UNIQUE CONSTRAINT (branch_code, year, round, level, stage, category)
```

## Getting Started

### Prerequisites

Ensure you have **Python 3.10+** and **uv** installed.

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/Pranav-Pardeshii/CoRe.git
cd CoRe
```

**2. Install dependencies**

Sync project dependencies deterministically using `uv`:

```bash
uv sync
```

**3. Environment configuration**

Create a `.env` file inside the `backend/` directory with your relational database credentials:

```env
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PORT=your-db-port
DB_PASS=your-db-password
DB_NAME=your-db-name
DB_SSL_CA=./backend/ca.pem
```

> **Note:** If your database provider requires SSL, ensure your CA certificate is saved securely at `backend/ca.pem`.

**4. Execution**

Start the FastAPI backend:

```bash
uv run uvicorn backend.main:app --reload
```

Start the Streamlit frontend (in a separate terminal window):

```bash
uv run streamlit run frontend/ui.py
```

## Roadmap

- [ ] **Stateful User Sessions** — Implement user registration and secure token-based authentication (via `python-jose` JWT) to allow personalized college shortlists.
- [ ] **Advanced Filter Matrix** — Expand query granularities to split categories by gender, home-university allocation, and distinct sub-caste groups.
- [ ] **Pipeline Automation** — Fully automate the multi-stage ETL process into a single-command CLI execution for future CAP round releases.
