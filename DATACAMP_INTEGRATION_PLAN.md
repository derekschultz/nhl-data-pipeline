# DataCamp Data Engineering Track — Project Plan

## Strategy

Build an end-to-end NHL data pipeline alongside the DataCamp Data Engineering career track. Each course maps to a concrete project milestone, reinforcing concepts through hands-on application.

---

## Phase 1: Finish Associate Data Engineer in SQL

### Course: Understanding Data Warehousing

- Design the data warehouse schema for NHL stats
- Document the star schema: `fact_game_skater_stats`, `fact_game_goalie_stats` with dimensions `dim_player`, `dim_team`, `dim_season`, `dim_game`
- Write the DDL scripts to create these tables in PostgreSQL
- Document decisions: why star schema over snowflake, grain of each fact table

### Course: Introduction to Snowflake

- Optional: replicate the PostgreSQL schema in a Snowflake free trial
- Document the architectural differences (storage/compute separation, warehouses, stages)

---

## Phase 2: Data Engineer in Python Track

This is where the bulk of the project work happens. ~57 hours of coursework with direct project applications.

### Course 1: Understanding Cloud Computing

- Add an `architecture/` folder with a system design diagram (draw.io or Mermaid)
- Document which components could live where: compute (EC2/Cloud Run), storage (S3/GCS), database (RDS/Cloud SQL)
- Add a `docs/architecture.md` explaining the cloud deployment plan

### Course 2-3: Introduction to Python / Intermediate Python

**You already know Python well.** Speed through these.

- Use this time to build the core data models in `src/models/`
- Write clean, well-documented Python classes for Player, Team, Game, GameStats
- Use dataclasses for clear data structures

### Course 4-5: Importing Data in Python / Intermediate Importing Data

- Build the NHL API client (`src/extract/nhl_api.py`)
- Implement extractors for:
  - Player stats: `https://api-web.nhle.com/v1/player/{id}/landing`
  - Game logs: `https://api-web.nhle.com/v1/score/{date}`
  - Standings: `https://api-web.nhle.com/v1/standings/{date}`
  - Schedule: `https://api-web.nhle.com/v1/schedule/{date}`
- Handle pagination, rate limiting, error retries
- Write extracted data to CSV staging files

### Course 6: Introduction to APIs in Python

- Enhance the NHL API client with proper session management, retry logic, response validation
- Add a `src/extract/draftkings_public.py` for pulling publicly available salary/slate data
- Implement proper logging for all API interactions

### Course 7: Cleaning Data in Python

- Build the transform layer (`src/transform/`)
- Implement cleaning functions:
  - Player name normalization (accents, suffixes, nicknames)
  - Team abbreviation standardization
  - Handle missing data, duplicate records, type casting
  - Validate statistical ranges (TOI, shot %, save %)
- Write unit tests for every cleaning function

### Course 8: Streamlined Data Ingestion with pandas

- Build pandas-based ingestion from multiple sources:
  - CSV files (staged API extracts)
  - JSON (NHL API responses)
  - SQL (read from PostgreSQL)
- Implement incremental loading (only fetch new games since last run)

### Course 9-10: Introduction to Git / Intermediate Git

**You already use Git.** Speed through these.

- Make sure the repo has clean branching practices
- Set up branch protection on main, use feature branches
- Write a solid README.md and CONTRIBUTING.md

### Course 11: Software Engineering for Data Scientists in Python

- Refactor into a proper Python package structure with `pyproject.toml`
- Add comprehensive unit tests (`tests/` directory with pytest)
- Set up CI with GitHub Actions (lint, test, type-check on every push)
- Add type hints throughout, run mypy
- Write docstrings for public API functions

### Course 12: Project — Code Review

Apply what you learned about software engineering practices by reviewing your own project code for adherence to best practices.

### Course 13: ETL and ELT in Python *(This is the big one)*

- Build the full ETL pipeline (`src/pipeline/`):
  - **Extract:** NHL API → raw JSON/CSV files in `data/raw/`
  - **Transform:** Clean, normalize, calculate derived metrics → `data/processed/`
  - **Load:** Insert into PostgreSQL tables
- Implement:
  - `src/pipeline/extract.py` — orchestrates all API extractors
  - `src/pipeline/transform.py` — runs all cleaning/enrichment steps
  - `src/pipeline/load.py` — upserts into PostgreSQL with conflict handling
  - `src/pipeline/run.py` — ties it all together
- Add logging, error handling, idempotency (re-running doesn't duplicate data)
- Track pipeline metadata: last run time, records processed, errors encountered

### Course 14: Introduction to Airflow in Python

- Create Airflow DAGs (`dags/`):
  - `daily_nhl_stats.py` — runs nightly after games complete
    - Task 1: Extract new game data from NHL API
    - Task 2: Transform and clean
    - Task 3: Load into PostgreSQL
    - Task 4: Run derived metric calculations
  - `weekly_standings.py` — weekly standings snapshot
- Configure with Docker Compose (Airflow + PostgreSQL)
- Add monitoring: email/Slack alerts on failure

### Course 15: Project — Walmart E-commerce Pipeline

Complete the DataCamp project, then compare their pipeline patterns against yours.

---

## Phase 3: Professional Data Engineer Track (Future)

Once you finish the Data Engineer in Python track, these are the next concepts to layer in:

| Topic | Project Application |
|-------|---------------------|
| **Docker** | Docker Compose for full stack: Airflow + PostgreSQL + Streamlit dashboard |
| **dbt** | Replace raw SQL transforms with dbt models, add tests and documentation |
| **PySpark** | Process full season datasets (millions of rows of play-by-play data) |
| **NoSQL** | Store unstructured data (game event feeds, shift charts) in MongoDB |
| **CI/CD** | GitHub Actions: test → build Docker image → deploy |

---

## Target Architecture

```
nhl-data-pipeline/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── Makefile
│
├── src/
│   ├── __init__.py
│   ├── models/                    # Data models
│   │   ├── __init__.py
│   │   ├── player.py
│   │   ├── team.py
│   │   ├── game.py
│   │   └── stats.py
│   │
│   ├── extract/                   # Data extraction layer
│   │   ├── __init__.py
│   │   ├── nhl_api.py            # NHL API client
│   │   └── utils.py              # Retry logic, rate limiting
│   │
│   ├── transform/                 # Data transformation layer
│   │   ├── __init__.py
│   │   ├── clean.py              # Data cleaning functions
│   │   ├── normalize.py          # Name/team normalization
│   │   └── metrics.py            # Derived metric calculations
│   │
│   ├── load/                      # Data loading layer
│   │   ├── __init__.py
│   │   ├── postgres.py           # PostgreSQL loader
│   │   └── models.py             # SQLAlchemy table definitions
│   │
│   ├── pipeline/                  # Pipeline orchestration
│   │   ├── __init__.py
│   │   └── run.py                # Full pipeline runner
│   │
│   └── dashboard/                 # Streamlit dashboard
│       ├── __init__.py
│       └── app.py
│
├── dags/                          # Airflow DAGs
│   ├── daily_nhl_stats.py
│   └── weekly_standings.py
│
├── sql/                           # Database DDL and migrations
│   ├── schema.sql
│   └── seed.sql
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_extract.py
│   ├── test_transform.py
│   └── test_load.py
│
├── docs/                          # Documentation
│   └── architecture.md
│
└── data/                          # Local data (gitignored)
    ├── raw/
    └── processed/
```

---

## Timeline Estimate

| Phase | DataCamp Track | Duration | Project Milestone |
|-------|---------------|----------|-------------------|
| 1 | Finish Associate DE in SQL | 1-2 weeks | Schema designed |
| 2a | DE in Python (Courses 1-6) | 3-4 weeks | API extraction layer complete, data models built |
| 2b | DE in Python (Courses 7-10) | 2-3 weeks | Transform layer complete, Git/testing practices solid |
| 2c | DE in Python (Courses 11-15) | 3-4 weeks | Full ETL pipeline, Airflow DAGs, CI/CD |
| 3 | Professional DE (future) | 6-8 weeks | Docker, dbt, PySpark, full production stack |

---

## Key Principles

1. **Course first, then code.** Don't get ahead of the coursework. Let each course inform the implementation.
2. **Commit often.** Each course module should result in at least one meaningful commit.
3. **Document as you go.** The README should evolve into a portfolio narrative.
4. **Don't over-engineer early.** Start simple (CSV → PostgreSQL), add complexity (Airflow, dbt, Docker) as you learn it.
