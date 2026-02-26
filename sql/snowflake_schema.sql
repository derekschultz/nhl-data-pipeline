-- NHL Data Pipeline: Snowflake Star Schema
-- Adapted from sql/schema.sql for Snowflake
--
-- Key differences from PostgreSQL version:
--   - No foreign key enforcement (Snowflake supports FK syntax for documentation
--     but does not enforce them — query optimizer uses them as hints)
--   - SERIAL → AUTOINCREMENT
--   - REAL → FLOAT
--   - TEXT → VARCHAR (Snowflake treats them identically, but VARCHAR is conventional)
--   - No explicit indexes (Snowflake uses automatic micro-partitioning and
--     pruning instead of B-tree indexes)
--   - CURRENT_TIMESTAMP() is a function call in Snowflake

-- ============================================================
-- DATABASE AND SCHEMA SETUP
-- ============================================================

CREATE DATABASE IF NOT EXISTS NHL;
CREATE SCHEMA IF NOT EXISTS NHL.PUBLIC;
USE SCHEMA NHL.PUBLIC;

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_season (
    season_id       VARCHAR(8) PRIMARY KEY,         -- e.g., '20252026'
    start_year      INTEGER NOT NULL,
    end_year        INTEGER NOT NULL,
    season_type     VARCHAR(16) NOT NULL DEFAULT 'regular'  -- 'regular', 'playoffs'
);

CREATE TABLE IF NOT EXISTS dim_team (
    team_abbrev     VARCHAR(3) PRIMARY KEY,         -- e.g., 'COL'
    full_name       VARCHAR(64) NOT NULL,           -- e.g., 'Colorado Avalanche'
    division        VARCHAR(16) NOT NULL,
    conference      VARCHAR(8) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_player (
    player_id       INTEGER PRIMARY KEY,
    first_name      VARCHAR(64) NOT NULL,
    last_name       VARCHAR(64) NOT NULL,
    position        VARCHAR(2) NOT NULL,            -- C, LW, RW, D, G
    team_abbrev     VARCHAR(3) REFERENCES dim_team(team_abbrev),
    jersey_number   INTEGER,
    shoots_catches  VARCHAR(1),                     -- L, R
    birth_date      DATE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS dim_game (
    game_id         INTEGER PRIMARY KEY,
    season_id       VARCHAR(8) REFERENCES dim_season(season_id),
    game_type       INTEGER NOT NULL,               -- 2 = regular, 3 = playoffs
    game_date       DATE NOT NULL,
    home_team       VARCHAR(3) REFERENCES dim_team(team_abbrev),
    away_team       VARCHAR(3) REFERENCES dim_team(team_abbrev),
    home_score      INTEGER,
    away_score      INTEGER,
    venue           VARCHAR(128),
    game_state      VARCHAR(8)                      -- FUT, LIVE, OFF, FINAL
);

-- ============================================================
-- FACT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_game_skater_stats (
    player_id           INTEGER REFERENCES dim_player(player_id),
    game_id             INTEGER REFERENCES dim_game(game_id),
    team_abbrev         VARCHAR(3) REFERENCES dim_team(team_abbrev),
    goals               INTEGER DEFAULT 0,
    assists             INTEGER DEFAULT 0,
    points              INTEGER DEFAULT 0,
    shots               INTEGER DEFAULT 0,
    hits                INTEGER DEFAULT 0,
    blocked_shots       INTEGER DEFAULT 0,
    pim                 INTEGER DEFAULT 0,
    toi_seconds         INTEGER DEFAULT 0,
    plus_minus          INTEGER DEFAULT 0,
    power_play_goals    INTEGER DEFAULT 0,
    power_play_points   INTEGER DEFAULT 0,
    shorthanded_goals   INTEGER DEFAULT 0,
    faceoff_pct         FLOAT,
    goals_rolling_10        FLOAT,
    assists_rolling_10      FLOAT,
    points_rolling_10       FLOAT,
    shots_rolling_10        FLOAT,
    toi_seconds_rolling_10  FLOAT,
    PRIMARY KEY (player_id, game_id)
);

CREATE TABLE IF NOT EXISTS fact_game_goalie_stats (
    player_id               INTEGER REFERENCES dim_player(player_id),
    game_id                 INTEGER REFERENCES dim_game(game_id),
    team_abbrev             VARCHAR(3) REFERENCES dim_team(team_abbrev),
    decision                VARCHAR(1),             -- W, L, O
    shots_against           INTEGER DEFAULT 0,
    saves                   INTEGER DEFAULT 0,
    goals_against           INTEGER DEFAULT 0,
    toi_seconds             INTEGER DEFAULT 0,
    save_pct                FLOAT,
    power_play_saves        INTEGER DEFAULT 0,
    shorthanded_saves       INTEGER DEFAULT 0,
    even_strength_saves     INTEGER DEFAULT 0,
    save_pct_rolling_10     FLOAT,
    goals_against_rolling_10 FLOAT,
    PRIMARY KEY (player_id, game_id)
);

-- ============================================================
-- PIPELINE METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          INTEGER AUTOINCREMENT PRIMARY KEY,
    run_date        DATE NOT NULL,
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    completed_at    TIMESTAMP,
    status          VARCHAR(16) NOT NULL DEFAULT 'running',  -- running, success, failed
    rows_extracted  INTEGER DEFAULT 0,
    rows_loaded     INTEGER DEFAULT 0,
    error_message   VARCHAR(4096)
);

-- ============================================================
-- NOTE ON INDEXES
-- ============================================================
-- Snowflake does not support user-created indexes. Instead it uses:
--   - Automatic micro-partitioning: data is divided into contiguous
--     storage units (50-500 MB compressed) based on insertion order
--   - Partition pruning: queries automatically skip partitions that
--     don't match WHERE clause predicates
--   - Clustering keys (optional): for very large tables, you can define
--     clustering keys to co-locate related rows. Not needed at our scale.
--
-- The PostgreSQL schema's indexes on game_date, player_id, etc. are
-- handled automatically by Snowflake's pruning engine.
