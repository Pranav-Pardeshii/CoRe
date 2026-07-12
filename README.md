# CoRe

CoRe is a college predictor for MHT-CET (Maharashtra's engineering entrance exam). Enter your percentile and category, and it shows which colleges and branches you're realistically eligible for, based on the previous years' actual CAP round cutoff data, plus how a college's cutoff has moved across rounds and years.

**Live app:** https://core-ui-733w.onrender.com

## Features

- Search eligible colleges by percentile, category, branch, and division
- Per-college cutoff trend graphs, split by year, across all available CAP rounds
- Public browsing — no login required

## Tech stack

- **Backend:** FastAPI, MySQL (hosted on Aiven), JWT auth (`python-jose`), Pydantic v2
- **Frontend:** Streamlit, Altair (for trend charts)
- **Dependency management:** [uv](https://docs.astral.sh/uv/)

## Running locally

1. Clone the repo
```
git clone https://github.com/Pranav-Pardeshii/CoRe.git
cd CoRe
```

2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it, then sync dependencies:
```
uv sync
```

3. Set up your environment variables. Create `backend/.env` with your database credentials:
```
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PORT=your-db-port
DB_PASS=your-db-password
DB_NAME=your-db-name
DB_SSL_CA=./backend/ca.pem
```
(You'll also need your database's CA certificate saved as `backend/ca.pem` if your provider requires SSL.)

4. Run the FastAPI backend
```
uv run uvicorn backend.main:app --reload
```

5. In a separate terminal, run the Streamlit frontend
```
uv run streamlit run frontend/ui.py
```
Open the URL shown in your terminal.

## Data

Cutoff data is sourced from official MHT-CET CAP round PDFs, parsed and loaded via the scripts in `etl/`. Currently covers 2024 (3 rounds) and 2025 (4 rounds).

### Database schema

Three tables, normalized around `branch_code` as the shared key:

```
colleges
├── college_code   VARCHAR(10)   PRIMARY KEY
├── college_name   VARCHAR(300)  NOT NULL
├── status         VARCHAR(300)
└── division       VARCHAR(100)

branches
├── branch_code    VARCHAR(15)   PRIMARY KEY
├── branch_name    VARCHAR(300)  NOT NULL
└── college_code    VARCHAR(10)  NOT NULL  → FK → colleges.college_code

cutoffs
├── id             INT           PRIMARY KEY, AUTO_INCREMENT
├── branch_code    VARCHAR(15)   NOT NULL   → FK → branches.branch_code
├── year           SMALLINT      NOT NULL
├── round          TINYINT       NOT NULL
├── level          VARCHAR(10)   NOT NULL
├── stage          VARCHAR(5)    NOT NULL
├── category       VARCHAR(20)   NOT NULL
├── rank           INT           NOT NULL
└── percentile     FLOAT         NOT NULL

UNIQUE (branch_code, year, round, level, stage, category)
```

One row in `cutoffs` = one category's cutoff for one branch, in one specific CAP round/year. `colleges` → `branches` → `cutoffs` is a one-to-many chain, so a single college can have many branches, and each branch accumulates cutoff rows across every year/round/category combination it's been offered under.

## Roadmap

- [ ] User accounts + saved college shortlists
- [ ] More granular category filters (gender / home-university / caste as separate fields)
- [ ] Additional historical years, once data formatting is normalized
