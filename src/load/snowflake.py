"""Snowflake data loader."""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def get_connection() -> "snowflake.connector.SnowflakeConnection":  # type: ignore[name-defined]  # noqa: F821
    """Create a Snowflake connection from environment variables.

    Expected env vars:
        SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
        SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_WAREHOUSE
    """
    import snowflake.connector  # type: ignore[import-not-found]

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ.get("SNOWFLAKE_DATABASE", "NHL"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    )


def load_dataframe(
    df: pd.DataFrame,
    table_name: str,
    conn: "snowflake.connector.SnowflakeConnection",  # type: ignore[name-defined]  # noqa: F821
) -> int:
    """Load a DataFrame into a Snowflake table using write_pandas.

    Args:
        df: Data to load.
        table_name: Target table name.
        conn: Active Snowflake connection.

    Returns:
        Number of rows loaded.
    """
    from snowflake.connector.pandas_tools import write_pandas  # type: ignore[import-not-found]

    success, _num_chunks, num_rows, _output = write_pandas(
        conn, df, table_name.upper(), auto_create_table=True, overwrite=False,
    )

    if success:
        logger.info("Loaded %d rows into Snowflake table %s", num_rows, table_name)
    else:
        logger.error("Failed to load data into Snowflake table %s", table_name)

    return int(num_rows)
