# NHL Data Pipeline

An end-to-end data engineering pipeline that ingests NHL game data from public APIs, transforms it into analytics-ready datasets, and serves it through a dashboard.

Built as a hands-on companion to DataCamp's Data Engineering career track.

## Architecture

```
NHL API ──→ Extract ──→ Transform ──→ Load ──→ PostgreSQL/Snowflake
                                                       │
                                                   dbt models
                                                   (staging + marts)
                                                       │
                                                   Dashboard
                                                       ↑
                                                 Airflow (orchestration)
```

**Extract:** Pull game stats, player data, standings, and schedules from the NHL public API.

**Transform:** Clean, normalize, and calculate derived metrics (rolling averages, pace stats, shooting efficiency).

**Load:** Upsert into a PostgreSQL or Snowflake data warehouse with a star schema design.

**Model:** dbt staging views clean raw tables; mart tables aggregate into player season stats, team standings, and goalie rankings.

**Orchestrate:** Airflow DAGs run nightly to ingest new game data.

**Serve:** Streamlit dashboard for exploring league trends and team performance.

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
# Install dbt dependencies
pip install -e ".[dbt]"
cd dbt && dbt deps

# Run all models (requires Snowflake env vars or --target postgres)
dbt run
dbt test

# Generate and serve docs
dbt docs generate && dbt docs serve
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
