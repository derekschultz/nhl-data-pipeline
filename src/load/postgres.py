"""PostgreSQL data loader."""

import logging
import os

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


def _delete_existing(engine: Engine, table_name: str, df: pd.DataFrame) -> int:
    """Delete rows from the target table that match incoming data on primary keys.

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
    if_exists: str = "append",
) -> int:
    """Load a DataFrame into a PostgreSQL table.

    Deletes existing rows matching primary keys before inserting
    to prevent duplicates on re-runs.

    Args:
        df: Data to load.
        table_name: Target table name.
        engine: SQLAlchemy engine.
        if_exists: How to handle existing data ('append', 'replace', 'fail').

    Returns:
        Number of rows inserted.
    """
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
        return result.scalar_one()
