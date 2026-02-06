# NHL Data Pipeline

An end-to-end data engineering pipeline that ingests NHL game data from public APIs, transforms it into analytics-ready datasets, and serves it through a dashboard.

Built as a hands-on companion to DataCamp's Data Engineering career track.

## Architecture

```
NHL API ──→ Extract ──→ Transform ──→ Load ──→ PostgreSQL / Snowflake
               │            │           │              │
          httpx client   clean &     star           dbt staging
          + retry        normalize   schema         + mart models
                         + metrics                     │
                                                 Streamlit Dashboard
                                                       ↑
                                                 Airflow (orchestration)
```

**Extract:** Pull game stats and boxscores from the NHL public API with automatic retries.

**Transform:** Clean player names, normalize team abbreviations, and calculate derived metrics.

**Load:** Insert into a PostgreSQL or Snowflake star schema (dimension + fact tables).

**Model:** dbt staging views enrich raw tables; mart tables aggregate into player season stats, team standings, and goalie rankings.

**Orchestrate:** Airflow DAGs run nightly to ingest new game data.

**Serve:** Streamlit dashboard with progressive display — works with seed data alone, shows richer analytics as the pipeline and dbt populate the database.

## Tech Stack

- **Language:** Python 3.11+
- **Database:** PostgreSQL 16 / Snowflake
- **Orchestration:** Apache Airflow
- **Transformations:** dbt (dbt-core + dbt-snowflake)
- **Containerization:** Docker / Docker Compose
- **Dashboard:** Streamlit
- **CI/CD:** GitHub Actions

## Project Structure

```
nhl-data-pipeline/
├── src/
│   ├── models/          # Data models (Player, Team, Game, Stats)
│   ├── extract/         # NHL API client and data extractors
│   ├── transform/       # Cleaning, normalization, derived metrics
│   ├── load/            # PostgreSQL loader and table definitions
│   ├── pipeline/        # Pipeline orchestration
│   └── dashboard/       # Streamlit dashboard
├── dbt/                 # dbt project (staging + mart models)
├── dags/                # Airflow DAGs
├── sql/                 # Database DDL and migrations
├── tests/               # Test suite
├── docs/                # Architecture documentation
└── data/                # Local staging data (gitignored)
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Docker (optional, for full stack)

### Installation

```bash
git clone https://github.com/derekschultz/nhl-data-pipeline.git
cd nhl-data-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Start the database

```bash
docker compose up -d  # PostgreSQL 16 with schema + seed data (32 NHL teams)
```

### Launch the dashboard

```bash
make dashboard  # Works with seed data alone
```

### Run the pipeline

```bash
# Extract today's game data
python -m src.pipeline.run --extract

# Run full ETL
python -m src.pipeline.run
```

### Run dbt models

```bash
# Install dbt dependencies (one-time)
pip install -e ".[dbt]"
cd dbt && dbt deps && cd ..

# Run models and tests (targets Postgres by default)
make dbt-run
make dbt-test

# Generate and serve docs
make dbt-docs
```

## Database Schema

Star schema design with two fact tables and four dimension tables:

- `fact_game_skater_stats` — per-game stats for skaters
- `fact_game_goalie_stats` — per-game stats for goalies
- `dim_player` — player attributes
- `dim_team` — team information
- `dim_game` — game details (date, venue, home/away)
- `dim_season` — season metadata

See `sql/schema.sql` for full DDL.

### dbt Models

dbt builds analytics on top of the raw star schema:

- **Staging (views):** `stg_players`, `stg_games`, `stg_skater_stats`, `stg_goalie_stats` — cleaned and enriched versions of raw tables
- **Marts (tables):** `mart_player_season_stats`, `mart_team_standings`, `mart_goalie_rankings` — aggregated analytics tables

## Development

```bash
# Run tests
pytest tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT
