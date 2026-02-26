"""Post-load enrichment: compute rolling averages for loaded game data.

After the load step inserts fact rows (with rolling columns NULL),
this module queries player history from the database, computes rolling
averages using the existing metrics module, and writes them back.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.transform.metrics import add_rolling_averages

logger = logging.getLogger(__name__)

ROLLING_WINDOW = 10

SKATER_ROLLING_STATS = ["goals", "assists", "points", "shots", "toi_seconds"]
GOALIE_ROLLING_STATS = ["save_pct", "goals_against"]


def run_enrich(game_date: date, backend: str = "postgres") -> int:
    """Compute and store rolling averages for players who played on game_date.

    Returns:
        Total number of rows updated across both fact tables.
    """
    logger.info("Enriching rolling averages for %s (backend=%s)", game_date, backend)

    if backend == "snowflake":
        return _enrich_snowflake(game_date)
    return _enrich_postgres(game_date)


# ── Postgres ─────────────────────────────────────────────────────────

def _enrich_postgres(game_date: date) -> int:
    """Compute and store rolling averages in Postgres."""
    from src.load.postgres import get_engine

    engine = get_engine()
    total = 0
    total += _enrich_skaters_postgres(engine, game_date)
    total += _enrich_goalies_postgres(engine, game_date)
    logger.info("Enrichment complete: %d rows updated for %s", total, game_date)
    return total


def _get_affected_player_ids(
    engine: Engine, fact_table: str, game_date: date,
) -> list[int]:
    """Get player IDs that have rows for games on the given date."""
    query = text(
        f"SELECT DISTINCT s.player_id "  # noqa: S608
        f"FROM {fact_table} s "
        f"JOIN dim_game g ON s.game_id = g.game_id "
        f"WHERE g.game_date = :game_date"
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"game_date": game_date}).fetchall()
    return [int(r[0]) for r in rows]


def _fetch_player_history(
    engine: Engine, fact_table: str, stat_columns: list[str], player_ids: list[int],
) -> pd.DataFrame:
    """Fetch full game history for the given players, joined to dim_game for date."""
    cols = ", ".join(f"s.{c}" for c in stat_columns)
    placeholders = ", ".join(f":p{i}" for i in range(len(player_ids)))
    params: dict[str, Any] = {f"p{i}": pid for i, pid in enumerate(player_ids)}

    query = text(
        f"SELECT s.player_id, s.game_id, g.game_date, {cols} "  # noqa: S608
        f"FROM {fact_table} s "
        f"JOIN dim_game g ON s.game_id = g.game_id "
        f"WHERE s.player_id IN ({placeholders}) "
        f"ORDER BY s.player_id, g.game_date"
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)


def _update_rolling_postgres(
    engine: Engine, fact_table: str, rolling_cols: list[str], df: pd.DataFrame,
) -> int:
    """UPDATE rolling columns for the given (player_id, game_id) rows."""
    set_clause = ", ".join(f"{c} = :{c}" for c in rolling_cols)
    query = text(
        f"UPDATE {fact_table} SET {set_clause} "  # noqa: S608
        f"WHERE player_id = :player_id AND game_id = :game_id"
    )

    subset = df[["player_id", "game_id", *rolling_cols]]
    clean = subset.astype(object).where(subset.notna(), other=None)  # type: ignore[arg-type]
    records: list[dict[str, Any]] = clean.to_dict(orient="records")  # type: ignore[assignment]

    with engine.connect() as conn:
        conn.execute(query, records)  # type: ignore[arg-type]
        conn.commit()

    return len(records)


def _enrich_skaters_postgres(engine: Engine, game_date: date) -> int:
    """Compute and store skater rolling averages."""
    player_ids = _get_affected_player_ids(engine, "fact_game_skater_stats", game_date)
    if not player_ids:
        logger.info("No skaters to enrich for %s", game_date)
        return 0

    logger.info("Enriching rolling averages for %d skaters", len(player_ids))
    df = _fetch_player_history(
        engine, "fact_game_skater_stats", SKATER_ROLLING_STATS, player_ids,
    )

    df = add_rolling_averages(df, SKATER_ROLLING_STATS, window=ROLLING_WINDOW)

    rolling_cols = [f"{s}_rolling_{ROLLING_WINDOW}" for s in SKATER_ROLLING_STATS]
    return _update_rolling_postgres(engine, "fact_game_skater_stats", rolling_cols, df)


def _enrich_goalies_postgres(engine: Engine, game_date: date) -> int:
    """Compute and store goalie rolling averages."""
    player_ids = _get_affected_player_ids(engine, "fact_game_goalie_stats", game_date)
    if not player_ids:
        logger.info("No goalies to enrich for %s", game_date)
        return 0

    logger.info("Enriching rolling averages for %d goalies", len(player_ids))
    df = _fetch_player_history(
        engine, "fact_game_goalie_stats", GOALIE_ROLLING_STATS, player_ids,
    )

    df = add_rolling_averages(df, GOALIE_ROLLING_STATS, window=ROLLING_WINDOW)

    rolling_cols = [f"{s}_rolling_{ROLLING_WINDOW}" for s in GOALIE_ROLLING_STATS]
    return _update_rolling_postgres(engine, "fact_game_goalie_stats", rolling_cols, df)


# ── Snowflake ────────────────────────────────────────────────────────

def _enrich_snowflake(game_date: date) -> int:
    """Compute and store rolling averages in Snowflake."""
    from src.load.snowflake import get_connection

    conn = get_connection()
    total = 0
    try:
        total += _enrich_skaters_snowflake(conn, game_date)
        total += _enrich_goalies_snowflake(conn, game_date)
    finally:
        conn.close()

    logger.info("Enrichment complete: %d rows updated for %s", total, game_date)
    return total


def _get_affected_player_ids_sf(
    conn: Any, fact_table: str, game_date: date,
) -> list[int]:
    """Get player IDs for the given date from Snowflake."""
    cur = conn.cursor()
    cur.execute(
        f"SELECT DISTINCT s.PLAYER_ID "
        f"FROM {fact_table.upper()} s "
        f"JOIN DIM_GAME g ON s.GAME_ID = g.GAME_ID "
        f"WHERE g.GAME_DATE = %s",
        (game_date,),
    )
    return [int(r[0]) for r in cur.fetchall()]


def _fetch_player_history_sf(
    conn: Any, fact_table: str, stat_columns: list[str], player_ids: list[int],
) -> pd.DataFrame:
    """Fetch player history from Snowflake."""
    upper_cols = ", ".join(f"s.{c.upper()}" for c in stat_columns)
    placeholders = ", ".join(["%s"] * len(player_ids))

    cur = conn.cursor()
    cur.execute(
        f"SELECT s.PLAYER_ID, s.GAME_ID, g.GAME_DATE, {upper_cols} "
        f"FROM {fact_table.upper()} s "
        f"JOIN DIM_GAME g ON s.GAME_ID = g.GAME_ID "
        f"WHERE s.PLAYER_ID IN ({placeholders}) "
        f"ORDER BY s.PLAYER_ID, g.GAME_DATE",
        player_ids,
    )
    columns = ["player_id", "game_id", "game_date", *stat_columns]
    rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def _update_rolling_snowflake(
    conn: Any, fact_table: str, rolling_cols: list[str], df: pd.DataFrame,
) -> int:
    """UPDATE rolling columns in Snowflake."""
    upper_table = fact_table.upper()
    set_clause = ", ".join(f"{c.upper()} = %s" for c in rolling_cols)

    cur = conn.cursor()
    for _, row in df.iterrows():
        values = [
            None if pd.isna(row[c]) else float(row[c]) for c in rolling_cols
        ]
        values.extend([int(row["player_id"]), int(row["game_id"])])
        cur.execute(
            f"UPDATE {upper_table} SET {set_clause} "
            f"WHERE PLAYER_ID = %s AND GAME_ID = %s",
            values,
        )

    return len(df)


def _enrich_skaters_snowflake(conn: Any, game_date: date) -> int:
    """Compute and store skater rolling averages in Snowflake."""
    player_ids = _get_affected_player_ids_sf(
        conn, "fact_game_skater_stats", game_date,
    )
    if not player_ids:
        logger.info("No skaters to enrich for %s", game_date)
        return 0

    logger.info("Enriching rolling averages for %d skaters", len(player_ids))
    df = _fetch_player_history_sf(
        conn, "fact_game_skater_stats", SKATER_ROLLING_STATS, player_ids,
    )

    df = add_rolling_averages(df, SKATER_ROLLING_STATS, window=ROLLING_WINDOW)

    rolling_cols = [f"{s}_rolling_{ROLLING_WINDOW}" for s in SKATER_ROLLING_STATS]
    return _update_rolling_snowflake(conn, "fact_game_skater_stats", rolling_cols, df)


def _enrich_goalies_snowflake(conn: Any, game_date: date) -> int:
    """Compute and store goalie rolling averages in Snowflake."""
    player_ids = _get_affected_player_ids_sf(
        conn, "fact_game_goalie_stats", game_date,
    )
    if not player_ids:
        logger.info("No goalies to enrich for %s", game_date)
        return 0

    logger.info("Enriching rolling averages for %d goalies", len(player_ids))
    df = _fetch_player_history_sf(
        conn, "fact_game_goalie_stats", GOALIE_ROLLING_STATS, player_ids,
    )

    df = add_rolling_averages(df, GOALIE_ROLLING_STATS, window=ROLLING_WINDOW)

    rolling_cols = [f"{s}_rolling_{ROLLING_WINDOW}" for s in GOALIE_ROLLING_STATS]
    return _update_rolling_snowflake(conn, "fact_game_goalie_stats", rolling_cols, df)
