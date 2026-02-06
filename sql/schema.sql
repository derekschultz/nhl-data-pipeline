-- NHL Data Pipeline: Star Schema
-- Fact tables + dimension tables for game-level statistics

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_season (
    season_id       TEXT PRIMARY KEY,       -- e.g., '20252026'
    start_year      INTEGER NOT NULL,
    end_year        INTEGER NOT NULL,
    season_type     TEXT NOT NULL DEFAULT 'regular'  -- 'regular', 'playoffs'
);

CREATE TABLE IF NOT EXISTS dim_team (
    team_abbrev     TEXT PRIMARY KEY,       -- e.g., 'COL'
    full_name       TEXT NOT NULL,          -- e.g., 'Colorado Avalanche'
    division        TEXT NOT NULL,
    conference      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_player (
    player_id       INTEGER PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    position        TEXT NOT NULL,          -- C, LW, RW, D, G
    team_abbrev     TEXT REFERENCES dim_team(team_abbrev),
    jersey_number   INTEGER,
    shoots_catches  TEXT,                   -- L, R
    birth_date      DATE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_game (
    game_id         INTEGER PRIMARY KEY,
    season_id       TEXT REFERENCES dim_season(season_id),
    game_type       INTEGER NOT NULL,       -- 2 = regular, 3 = playoffs
    game_date       DATE NOT NULL,
    home_team       TEXT REFERENCES dim_team(team_abbrev),
    away_team       TEXT REFERENCES dim_team(team_abbrev),
    home_score      INTEGER,
    away_score      INTEGER,
    venue           TEXT,
    game_state      TEXT                    -- FUT, LIVE, OFF, FINAL
);

-- ============================================================
-- FACT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_game_skater_stats (
    player_id           INTEGER REFERENCES dim_player(player_id),
    game_id             INTEGER REFERENCES dim_game(game_id),
    team_abbrev         TEXT REFERENCES dim_team(team_abbrev),
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
    faceoff_pct         REAL,
    PRIMARY KEY (player_id, game_id)
);

CREATE TABLE IF NOT EXISTS fact_game_goalie_stats (
    player_id               INTEGER REFERENCES dim_player(player_id),
    game_id                 INTEGER REFERENCES dim_game(game_id),
    team_abbrev             TEXT REFERENCES dim_team(team_abbrev),
    decision                TEXT,           -- W, L, O
    shots_against           INTEGER DEFAULT 0,
    saves                   INTEGER DEFAULT 0,
    goals_against           INTEGER DEFAULT 0,
    toi_seconds             INTEGER DEFAULT 0,
    save_pct                REAL,
    power_play_saves        INTEGER DEFAULT 0,
    shorthanded_saves       INTEGER DEFAULT 0,
    even_strength_saves     INTEGER DEFAULT 0,
    PRIMARY KEY (player_id, game_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_skater_stats_game ON fact_game_skater_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_skater_stats_player ON fact_game_skater_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_skater_stats_team ON fact_game_skater_stats(team_abbrev);
CREATE INDEX IF NOT EXISTS idx_goalie_stats_game ON fact_game_goalie_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_goalie_stats_player ON fact_game_goalie_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_game_date ON dim_game(game_date);
CREATE INDEX IF NOT EXISTS idx_game_season ON dim_game(season_id);

-- ============================================================
-- PIPELINE METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          SERIAL PRIMARY KEY,
    run_date        DATE NOT NULL,
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    status          TEXT NOT NULL DEFAULT 'running',  -- running, success, failed
    rows_extracted  INTEGER DEFAULT 0,
    rows_loaded     INTEGER DEFAULT 0,
    error_message   TEXT
);
