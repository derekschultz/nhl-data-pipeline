"""Snowflake data loader."""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

# Primary key columns used for deduplication before insert
TABLE_KEYS: dict[str, list[str]] = {
    "dim_player": ["PLAYER_ID"],
    "dim_game": ["GAME_ID"],
    "fact_game_skater_stats": ["PLAYER_ID", "GAME_ID"],
    "fact_game_goalie_stats": ["PLAYER_ID", "GAME_ID"],
}


def get_connection() -> "snowflake.connector.SnowflakeConnection":  # type: ignore[name-defined]  # noqa: F821
    """Create a Snowflake connection from environment variables.

    Expected env vars:
        SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
        SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_WAREHOUSE,
        SNOWFLAKE_ROLE
    """
    import snowflake.connector  # type: ignore[import-not-found]

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ.get("SNOWFLAKE_DATABASE", "NHL"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.environ.get("SNOWFLAKE_ROLE", "TRANSFORM"),
    )


def _delete_existing(
    conn: "snowflake.connector.SnowflakeConnection",  # type: ignore[name-defined]  # noqa: F821
    table_name: str,
    df: pd.DataFrame,
) -> int:
    """Delete rows from the target table that match incoming data on primary keys.

    Returns:
        Number of rows deleted.
    """
    upper_table = table_name.upper()
    keys = TABLE_KEYS.get(table_name, [])
    if not keys:
        return 0

    cur = conn.cursor()
    if len(keys) == 1:
        key = keys[0]
        values = df[key].dropna().unique().tolist()
        if not values:
            return 0
        placeholders = ", ".join(["%s"] * len(values))
        cur.execute(
            f"DELETE FROM {upper_table} WHERE {key} IN ({placeholders})",
            values,
        )
    else:
        # Composite key: delete with paired conditions
        pairs = df[keys].drop_duplicates().values.tolist()
        if not pairs:
            return 0
        conditions = " OR ".join(
            "(" + " AND ".join(f"{k} = %s" for k in keys) + ")"
            for _ in pairs
        )
        params = [val for pair in pairs for val in pair]
        cur.execute(f"DELETE FROM {upper_table} WHERE {conditions}", params)

    deleted: int = cur.rowcount or 0
    if deleted:
        logger.info("Deleted %d existing rows from %s", deleted, upper_table)
    return deleted


def load_dataframe(
    df: pd.DataFrame,
    table_name: str,
    conn: "snowflake.connector.SnowflakeConnection",  # type: ignore[name-defined]  # noqa: F821
) -> int:
    """Load a DataFrame into a Snowflake table using write_pandas.

    Deletes existing rows matching primary keys before inserting
    to prevent duplicates on re-runs.

    Args:
        df: Data to load.
        table_name: Target table name.
        conn: Active Snowflake connection.

    Returns:
        Number of rows loaded.
    """
    from snowflake.connector.pandas_tools import write_pandas  # type: ignore[import-not-found]

    # Snowflake expects uppercase column names to match DDL
    df = df.copy()
    df.columns = pd.Index([c.upper() for c in df.columns])

    _delete_existing(conn, table_name, df)

    success, _num_chunks, num_rows, _output = write_pandas(
        conn, df, table_name.upper(), auto_create_table=False, overwrite=False,
    )

    if success:
        logger.info("Loaded %d rows into Snowflake table %s", num_rows, table_name)
    else:
        logger.error("Failed to load data into Snowflake table %s", table_name)

    return int(num_rows)
