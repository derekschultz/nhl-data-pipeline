"""Backend selector for data loading."""

import os
from types import ModuleType


def get_loader(backend: str | None = None) -> ModuleType:
    """Return the appropriate loader module based on backend config.

    Args:
        backend: 'postgres' or 'snowflake'. Falls back to DB_BACKEND env var,
                 then defaults to 'postgres'.

    Returns:
        The loader module (src.load.postgres or src.load.snowflake).
    """
    if backend is None:
        backend = os.environ.get("DB_BACKEND", "postgres")

    if backend == "snowflake":
        from src.load import snowflake
        return snowflake
    else:
        from src.load import postgres
        return postgres
