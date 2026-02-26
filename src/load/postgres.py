"""PostgreSQL data loader."""

import logging
import os
from typing import Literal

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Primary key columns used for deduplication before insert
TABLE_KEYS: dict[str, list[str]] = {
    "dim_player": ["player_id"],
    "dim_game": ["game_id"],
    "fact_game_skater_stats": ["player_id", "game_id"],
    "fact_game_goalie_stats": ["player_id", "game_id"],
}

# Non-key columns per table, used to build ON CONFLICT DO UPDATE for dimension tables
_TABLE_COLUMNS: dict[str, list[str]] = {
    "dim_player": [
        "first_name", "last_name", "position", "team_abbrev",
        "jersey_number", "shoots_catches", "birth_date",
    ],
    "dim_game": [
        "season_id", "game_type", "game_date", "home_team", "away_team",
        "home_score", "away_score", "venue", "game_state",
    ],
}


def _build_connection_string() -> str:
    """Build a PostgreSQL connection string from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "nhl")
    user = os.getenv("POSTGRES_USER", "nhl")
    password = os.getenv("POSTGRES_PASSWORD", "nhl")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_engine(connection_string: str | None = None) -> Engine:
    """Create a SQLAlchemy engine."""
    return create_engine(connection_string or _build_connection_string())


def _upsert_dataframe(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """Upsert rows using INSERT ... ON CONFLICT DO UPDATE.

    Used for dimension tables that are referenced by fact table FKs,
    where delete-then-insert would violate constraints.
    """
    keys = TABLE_KEYS[table_name]
    update_cols = _TABLE_COLUMNS[table_name]
    all_cols = keys + update_cols

    # Only include columns that are actually in the dataframe
    all_cols = [c for c in all_cols if c in df.columns]
    update_cols = [c for c in update_cols if c in df.columns]

    placeholders = ", ".join(f":{c}" for c in all_cols)
    col_list = ", ".join(all_cols)
    conflict_keys = ", ".join(keys)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    sql = (
        f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict_keys}) DO UPDATE SET {update_set}"
    )

    # Convert NaN to None so psycopg2 sends NULL instead of float NaN
    records = df[all_cols].where(df[all_cols].notna(), None).to_dict(orient="records")
    with engine.connect() as conn:
        conn.execute(text(sql), records)
        conn.commit()


def _delete_existing(engine: Engine, table_name: str, df: pd.DataFrame) -> int:
    """Delete rows from the target table that match incoming data on primary keys.

    Used for fact tables (leaf tables with no FK dependents).

    Returns:
        Number of rows deleted.
    """
    keys = TABLE_KEYS.get(table_name, [])
    if not keys:
        return 0

    with engine.connect() as conn:
        if len(keys) == 1:
            key = keys[0]
            values = df[key].dropna().unique().tolist()
            if not values:
                return 0
            placeholders = ", ".join([f":v{i}" for i in range(len(values))])
            params = {f"v{i}": v for i, v in enumerate(values)}
            result = conn.execute(
                text(f"DELETE FROM {table_name} WHERE {key} IN ({placeholders})"),
                params,
            )
        else:
            # Composite key: delete with paired conditions
            pairs = df[keys].drop_duplicates().values.tolist()
            if not pairs:
                return 0
            conditions = " OR ".join(
                "(" + " AND ".join(f"{k} = :p{i}_{k}" for k in keys) + ")"
                for i, _ in enumerate(pairs)
            )
            params = {
                f"p{i}_{k}": pair[j]
                for i, pair in enumerate(pairs)
                for j, k in enumerate(keys)
            }
            result = conn.execute(
                text(f"DELETE FROM {table_name} WHERE {conditions}"),
                params,
            )

        deleted = result.rowcount
        conn.commit()

    if deleted:
        logger.info("Deleted %d existing rows from %s", deleted, table_name)
    return deleted


def load_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: Literal["fail", "replace", "append"] = "append",
) -> int:
    """Load a DataFrame into a PostgreSQL table.

    Dimension tables (dim_player, dim_game) use ON CONFLICT DO UPDATE to
    avoid FK violations from fact tables. Fact tables use delete-then-insert.

    Returns:
        Number of rows loaded.
    """
    if table_name in _TABLE_COLUMNS:
        # Dimension table: use proper upsert to avoid FK violations
        rows_before = _count_rows(engine, table_name)
        _upsert_dataframe(df, table_name, engine)
        rows_after = _count_rows(engine, table_name)
        rows_loaded = rows_after - rows_before
        logger.info("Loaded %d rows into %s (upsert)", rows_loaded, table_name)
        return rows_loaded

    # Fact table: safe to delete-then-insert (no FK dependents)
    _delete_existing(engine, table_name, df)

    rows_before = _count_rows(engine, table_name)
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    rows_after = _count_rows(engine, table_name)
    rows_inserted = rows_after - rows_before

    logger.info("Loaded %d rows into %s", rows_inserted, table_name)
    return rows_inserted


def _count_rows(engine: Engine, table_name: str) -> int:
    """Count rows in a table."""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))  # noqa: S608
        return int(result.scalar_one())
