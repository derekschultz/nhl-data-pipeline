"""PostgreSQL data loader."""

import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DEFAULT_CONNECTION_STRING = "postgresql://localhost:5432/nhl"


def get_engine(connection_string: str = DEFAULT_CONNECTION_STRING) -> Engine:
    """Create a SQLAlchemy engine."""
    return create_engine(connection_string)


def load_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "append",
) -> int:
    """Load a DataFrame into a PostgreSQL table.

    Args:
        df: Data to load.
        table_name: Target table name.
        engine: SQLAlchemy engine.
        if_exists: How to handle existing data ('append', 'replace', 'fail').

    Returns:
        Number of rows inserted.
    """
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
