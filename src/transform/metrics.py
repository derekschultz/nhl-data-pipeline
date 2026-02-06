"""Derived metric calculations for NHL stats."""

import pandas as pd


def add_rolling_averages(
    df: pd.DataFrame,
    stat_columns: list[str],
    window: int = 10,
    group_by: str = "player_id",
) -> pd.DataFrame:
    """Add rolling average columns for specified stats.

    Args:
        df: DataFrame sorted by game date with player stats.
        stat_columns: Column names to calculate rolling averages for.
        window: Number of games for the rolling window.
        group_by: Column to group by (usually player_id).

    Returns:
        DataFrame with new columns named '{stat}_rolling_{window}'.
    """
    df = df.sort_values(["player_id", "game_date"])

    for col in stat_columns:
        new_col = f"{col}_rolling_{window}"
        df[new_col] = (
            df.groupby(group_by)[col]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )

    return df
