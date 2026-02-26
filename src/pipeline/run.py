"""Main pipeline runner. Ties together extract, transform, and load stages."""

from __future__ import annotations

import argparse
import logging
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def run_extract(game_date: date) -> int:
    """Extract game data from NHL API for a given date.

    Fetches scores and boxscores for all completed games, parses into
    dataclasses, and writes CSV files to data/raw/.

    Returns:
        Number of rows extracted across all files.
    """
    from src.extract.nhl_api import NHLAPIClient
    from src.extract.parse import (
        parse_games,
        parse_goalie_stats,
        parse_players,
        parse_skater_stats,
    )

    logger.info("Extracting data for %s", game_date)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    date_str = game_date.isoformat()

    # Remove stale CSVs from prior runs so old data doesn't bleed through
    for old_csv in RAW_DIR.glob(f"{date_str}_*.csv"):
        old_csv.unlink()

    total_rows = 0

    with NHLAPIClient() as client:
        scores = client.get_scores(game_date)
        all_games = parse_games(scores)

        # Keep only regular-season and playoff games
        supported_game_types = {2, 3}
        games = [g for g in all_games if g.game_type in supported_game_types]

        if not games:
            skipped = len(all_games)
            logger.info(
                "No supported games found for %s (%d total skipped)",
                game_date, skipped,
            )
            return 0

        # Write games CSV
        games_df = pd.DataFrame([asdict(g) for g in games])
        games_df.to_csv(RAW_DIR / f"{date_str}_games.csv", index=False)
        total_rows += len(games_df)
        logger.info("Wrote %d games to raw CSV", len(games_df))

        # Fetch boxscores for completed games only
        completed_games = [g for g in games if g.is_final]
        logger.info(
            "%d of %d games are final regular-season/playoff, fetching boxscores",
            len(completed_games),
            len(games),
        )

        all_skaters: list[dict] = []
        all_goalies: list[dict] = []
        all_players: list[dict] = []

        for game in completed_games:
            try:
                boxscore = client.get_game_boxscore(game.game_id)
            except Exception:
                logger.warning("Skipping game %s: failed to fetch boxscore", game.game_id)
                continue

            skaters = parse_skater_stats(boxscore, game.game_id)
            all_skaters.extend(asdict(s) for s in skaters)

            goalies = parse_goalie_stats(boxscore, game.game_id)
            all_goalies.extend(asdict(g) for g in goalies)

            players = parse_players(boxscore)
            all_players.extend(asdict(p) for p in players)

        # Write skater stats
        if all_skaters:
            df = pd.DataFrame(all_skaters)
            df.to_csv(RAW_DIR / f"{date_str}_skater_stats.csv", index=False)
            total_rows += len(df)
            logger.info("Wrote %d skater stat lines to raw CSV", len(df))

        # Write goalie stats
        if all_goalies:
            df = pd.DataFrame(all_goalies)
            df.to_csv(RAW_DIR / f"{date_str}_goalie_stats.csv", index=False)
            total_rows += len(df)
            logger.info("Wrote %d goalie stat lines to raw CSV", len(df))

        # Write players (deduplicate across games)
        if all_players:
            df = pd.DataFrame(all_players).drop_duplicates(subset=["player_id"])
            df.to_csv(RAW_DIR / f"{date_str}_players.csv", index=False)
            total_rows += len(df)
            logger.info("Wrote %d unique players to raw CSV", len(df))

    logger.info("Extract complete: %d total rows for %s", total_rows, game_date)
    return total_rows


def run_transform(game_date: date) -> dict[str, pd.DataFrame]:
    """Transform raw extracted data into cleaned, enriched datasets.

    Returns:
        Dict of transformed DataFrames keyed by table name.
    """
    from src.transform.pipeline import run_transforms

    logger.info("Running transformations for %s", game_date)
    result = run_transforms(game_date)
    logger.info(
        "Transform complete: %s",
        {k: len(v) for k, v in result.items()},
    )
    return result


def run_load(game_date: date, backend: str = "postgres") -> int:
    """Load transformed data into the database.

    Loads dimension tables first (for FK constraints), then fact tables.

    Args:
        game_date: Date to load data for.
        backend: Database backend ('postgres' or 'snowflake').

    Returns:
        Total number of rows loaded.
    """
    logger.info("Loading data for %s into %s", game_date, backend)
    date_str = game_date.isoformat()
    total_rows = 0

    # Read transformed CSVs
    dataframes: dict[str, pd.DataFrame] = {}
    file_map = {
        "dim_player": f"{date_str}_players.csv",
        "dim_game": f"{date_str}_games.csv",
        "fact_game_skater_stats": f"{date_str}_skater_stats.csv",
        "fact_game_goalie_stats": f"{date_str}_goalie_stats.csv",
    }

    for table_name, filename in file_map.items():
        path = PROCESSED_DIR / filename
        if path.exists():
            dataframes[table_name] = pd.read_csv(path)

    if not dataframes:
        logger.warning("No processed data found for %s", game_date)
        return 0

    if backend == "snowflake":
        total_rows = _load_snowflake(dataframes)
    else:
        total_rows = _load_postgres(dataframes)

    logger.info("Load complete: %d total rows for %s", total_rows, game_date)
    return total_rows


def _ensure_seasons_postgres(engine: Engine, dataframes: dict[str, pd.DataFrame]) -> None:
    """Auto-insert any missing seasons referenced by dim_game data."""
    from sqlalchemy import text

    if "dim_game" not in dataframes:
        return

    df = _prepare_for_table(dataframes["dim_game"], "dim_game")
    if "season_id" not in df.columns:
        return

    season_ids = df["season_id"].dropna().unique().tolist()
    if not season_ids:
        return

    with engine.connect() as conn:
        for sid in season_ids:
            sid_str = str(sid)
            start_year = int(sid_str[:4])
            end_year = int(sid_str[4:])
            conn.execute(
                text(
                    "INSERT INTO dim_season (season_id, start_year, end_year, season_type) "
                    "VALUES (:sid, :start, :end, 'regular') "
                    "ON CONFLICT (season_id) DO NOTHING"
                ),
                {"sid": sid_str, "start": start_year, "end": end_year},
            )
        conn.commit()
        logger.info("Ensured seasons exist: %s", season_ids)


def _load_postgres(dataframes: dict[str, pd.DataFrame]) -> int:
    """Load DataFrames into PostgreSQL."""
    from src.load.postgres import get_engine, load_dataframe

    engine = get_engine()
    total = 0

    # Ensure referenced seasons exist before loading games
    _ensure_seasons_postgres(engine, dataframes)

    # Dimension tables first, then fact tables
    load_order = ["dim_player", "dim_game", "fact_game_skater_stats", "fact_game_goalie_stats"]
    for table_name in load_order:
        if table_name not in dataframes:
            continue
        df = _prepare_for_table(dataframes[table_name], table_name)
        rows = load_dataframe(df, table_name, engine)
        total += rows

    return total


def _ensure_seasons_snowflake(conn: object, dataframes: dict[str, pd.DataFrame]) -> None:
    """Auto-insert any missing seasons referenced by dim_game data (Snowflake)."""
    if "dim_game" not in dataframes:
        return

    df = _prepare_for_table(dataframes["dim_game"], "dim_game")
    if "season_id" not in df.columns:
        return

    season_ids = df["season_id"].dropna().unique().tolist()
    if not season_ids:
        return

    cur = conn.cursor()
    for sid in season_ids:
        sid_str = str(sid)
        start_year = int(sid_str[:4])
        end_year = int(sid_str[4:])
        cur.execute(
            "MERGE INTO DIM_SEASON AS target "
            "USING (SELECT %s AS SEASON_ID, %s AS START_YEAR, "
            "%s AS END_YEAR, 'regular' AS SEASON_TYPE) AS source "
            "ON target.SEASON_ID = source.SEASON_ID "
            "WHEN NOT MATCHED THEN INSERT (SEASON_ID, START_YEAR, END_YEAR, SEASON_TYPE) "
            "VALUES (source.SEASON_ID, source.START_YEAR, source.END_YEAR, source.SEASON_TYPE)",
            (sid_str, start_year, end_year),
        )
    logger.info("Ensured seasons exist in Snowflake: %s", season_ids)


def _load_snowflake(dataframes: dict[str, pd.DataFrame]) -> int:
    """Load DataFrames into Snowflake."""
    from src.load.snowflake import get_connection, load_dataframe

    conn = get_connection()
    total = 0

    try:
        # Ensure referenced seasons exist before loading games
        _ensure_seasons_snowflake(conn, dataframes)

        load_order = [
            "dim_player",
            "dim_game",
            "fact_game_skater_stats",
            "fact_game_goalie_stats",
        ]
        for table_name in load_order:
            if table_name not in dataframes:
                continue
            df = _prepare_for_table(dataframes[table_name], table_name)
            rows = load_dataframe(df, table_name, conn)
            total += rows
    finally:
        conn.close()

    return total


def _prepare_for_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Rename/select columns to match database schema."""
    df = df.copy()

    if table_name == "dim_game":
        rename = {
            "home_team_abbrev": "home_team",
            "away_team_abbrev": "away_team",
            "season": "season_id",
        }
        df = df.rename(columns=rename)
        columns = [
            "game_id", "season_id", "game_type", "game_date",
            "home_team", "away_team", "home_score", "away_score",
            "venue", "game_state",
        ]
        df = df[[c for c in columns if c in df.columns]]

    elif table_name == "dim_player":
        columns = [
            "player_id", "first_name", "last_name", "position",
            "team_abbrev", "jersey_number", "shoots_catches", "birth_date",
        ]
        df = df[[c for c in columns if c in df.columns]]

    elif table_name == "fact_game_skater_stats":
        columns = [
            "player_id", "game_id", "team_abbrev", "goals", "assists",
            "points", "shots", "hits", "blocked_shots", "pim",
            "toi_seconds", "plus_minus", "power_play_goals",
            "shorthanded_goals", "faceoff_pct",
        ]
        df = df[[c for c in columns if c in df.columns]]

    elif table_name == "fact_game_goalie_stats":
        columns = [
            "player_id", "game_id", "team_abbrev", "decision",
            "shots_against", "saves", "goals_against", "toi_seconds",
            "save_pct", "power_play_saves", "shorthanded_saves",
            "even_strength_saves",
        ]
        df = df[[c for c in columns if c in df.columns]]

    return df


def _update_pipeline_run(
    engine: object,
    run_id: int,
    status: str,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
    error_message: str | None = None,
) -> None:
    """Update pipeline_runs metadata table (Postgres via SQLAlchemy)."""
    from sqlalchemy import text
    from sqlalchemy.engine import Engine

    if not isinstance(engine, Engine):
        return

    with engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE pipeline_runs SET completed_at = :completed, status = :status, "
                "rows_extracted = :extracted, rows_loaded = :loaded, error_message = :error "
                "WHERE run_id = :run_id"
            ),
            {
                "completed": datetime.now(),
                "status": status,
                "extracted": rows_extracted,
                "loaded": rows_loaded,
                "error": error_message,
                "run_id": run_id,
            },
        )
        conn.commit()


def _create_pipeline_run_snowflake(game_date: date) -> int | None:
    """Insert a new pipeline_runs record in Snowflake. Returns run_id or None."""
    try:
        from src.load.snowflake import get_connection

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO pipeline_runs (run_date, status) VALUES (%s, 'running')",
                (game_date,),
            )
            cur.execute("SELECT MAX(run_id) FROM pipeline_runs")
            row = cur.fetchone()
            run_id = int(row[0]) if row and row[0] is not None else None
            return run_id
        finally:
            conn.close()
    except Exception:
        logger.debug("Could not create pipeline_runs record in Snowflake")
        return None


def _update_pipeline_run_snowflake(
    run_id: int,
    status: str,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
    error_message: str | None = None,
) -> None:
    """Update pipeline_runs metadata table in Snowflake."""
    try:
        from src.load.snowflake import get_connection

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE pipeline_runs SET completed_at = %s, status = %s, "
                "rows_extracted = %s, rows_loaded = %s, error_message = %s "
                "WHERE run_id = %s",
                (datetime.now(), status, rows_extracted, rows_loaded, error_message, run_id),
            )
        finally:
            conn.close()
    except Exception:
        logger.debug("Could not update pipeline_runs record in Snowflake")


def _create_pipeline_run(game_date: date) -> int | None:
    """Insert a new pipeline_runs record (Postgres). Returns run_id or None."""
    try:
        from sqlalchemy import text

        from src.load.postgres import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO pipeline_runs (run_date, status) "
                    "VALUES (:run_date, 'running') RETURNING run_id"
                ),
                {"run_date": game_date},
            )
            run_id = int(result.scalar_one())
            conn.commit()
            return run_id
    except Exception:
        logger.debug("Could not create pipeline_runs record (DB may not be available)")
        return None


def run_pipeline(game_date: date, backend: str = "postgres") -> None:
    """Run the full ETL pipeline for a given date."""
    logger.info("Starting pipeline for %s (backend=%s)", game_date, backend)

    if backend == "snowflake":
        run_id = _create_pipeline_run_snowflake(game_date)
    else:
        run_id = _create_pipeline_run(game_date)

    rows_extracted = 0
    rows_loaded = 0

    try:
        rows_extracted = run_extract(game_date)
        run_transform(game_date)
        rows_loaded = run_load(game_date, backend=backend)

        if run_id is not None:
            if backend == "snowflake":
                _update_pipeline_run_snowflake(
                    run_id, "success",
                    rows_extracted=rows_extracted, rows_loaded=rows_loaded,
                )
            else:
                from src.load.postgres import get_engine

                _update_pipeline_run(
                    get_engine(), run_id, "success",
                    rows_extracted=rows_extracted, rows_loaded=rows_loaded,
                )
    except Exception as e:
        if run_id is not None:
            try:
                if backend == "snowflake":
                    _update_pipeline_run_snowflake(
                        run_id, "failed",
                        rows_extracted=rows_extracted,
                        error_message=str(e),
                    )
                else:
                    from src.load.postgres import get_engine

                    _update_pipeline_run(
                        get_engine(), run_id, "failed",
                        rows_extracted=rows_extracted,
                        error_message=str(e),
                    )
            except Exception:
                pass
        raise

    logger.info("Pipeline complete for %s", game_date)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="NHL Data Pipeline")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Game date to process (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Process a range of dates (YYYY-MM-DD YYYY-MM-DD).",
    )
    parser.add_argument("--extract", action="store_true", help="Run extract only")
    parser.add_argument("--transform", action="store_true", help="Run transform only")
    parser.add_argument("--load", action="store_true", help="Run load only")
    parser.add_argument(
        "--backend",
        choices=["postgres", "snowflake"],
        default="postgres",
        help="Database backend (default: postgres).",
    )
    args = parser.parse_args()

    # Build list of dates to process
    if args.date_range:
        from src.extract.utils import date_range
        dates = date_range(
            date.fromisoformat(args.date_range[0]),
            date.fromisoformat(args.date_range[1]),
        )
    else:
        dates = [args.date]

    for game_date in dates:
        if args.extract:
            run_extract(game_date)
        elif args.transform:
            run_transform(game_date)
        elif args.load:
            run_load(game_date, backend=args.backend)
        else:
            run_pipeline(game_date, backend=args.backend)
