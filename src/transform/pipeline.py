"""Transform pipeline: orchestrates all transform steps on raw CSVs."""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.transform.clean import normalize_player_name, toi_to_seconds
from src.transform.normalize import normalize_position, normalize_team

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def run_transforms(game_date: date) -> dict[str, pd.DataFrame]:
    """Run all transform steps on raw CSVs for a given date.

    Args:
        game_date: The date to process.

    Returns:
        Dict of transformed DataFrames keyed by table name.
    """
    date_str = game_date.isoformat()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale processed CSVs from prior runs
    for old_csv in PROCESSED_DIR.glob(f"{date_str}_*.csv"):
        old_csv.unlink()

    result: dict[str, pd.DataFrame] = {}

    # Players
    players_path = RAW_DIR / f"{date_str}_players.csv"
    if players_path.exists():
        df = pd.read_csv(players_path)
        df["first_name"] = df["first_name"].apply(normalize_player_name)
        df["last_name"] = df["last_name"].apply(normalize_player_name)
        df["position"] = df["position"].apply(normalize_position)
        df["team_abbrev"] = df["team_abbrev"].apply(normalize_team)
        df.to_csv(PROCESSED_DIR / f"{date_str}_players.csv", index=False)
        result["dim_player"] = df
        logger.info("Transformed %d player records", len(df))

    # Games
    games_path = RAW_DIR / f"{date_str}_games.csv"
    if games_path.exists():
        df = pd.read_csv(games_path)
        df["home_team_abbrev"] = df["home_team_abbrev"].apply(normalize_team)
        df["away_team_abbrev"] = df["away_team_abbrev"].apply(normalize_team)
        df.to_csv(PROCESSED_DIR / f"{date_str}_games.csv", index=False)
        result["dim_game"] = df
        logger.info("Transformed %d game records", len(df))

    # Skater stats
    skater_path = RAW_DIR / f"{date_str}_skater_stats.csv"
    if skater_path.exists():
        df = pd.read_csv(skater_path)
        df["team_abbrev"] = df["team_abbrev"].apply(normalize_team)
        # Convert TOI string to seconds if still in string format
        if df["toi_seconds"].dtype == object:
            df["toi_seconds"] = df["toi_seconds"].apply(toi_to_seconds)
        # Ensure points column is computed
        if "points" not in df.columns or df["points"].isna().all():
            df["points"] = df["goals"] + df["assists"]
        df.to_csv(PROCESSED_DIR / f"{date_str}_skater_stats.csv", index=False)
        result["fact_game_skater_stats"] = df
        logger.info("Transformed %d skater stat records", len(df))

    # Goalie stats
    goalie_path = RAW_DIR / f"{date_str}_goalie_stats.csv"
    if goalie_path.exists():
        df = pd.read_csv(goalie_path)
        df["team_abbrev"] = df["team_abbrev"].apply(normalize_team)
        # Convert TOI string to seconds if still in string format
        if df["toi_seconds"].dtype == object:
            df["toi_seconds"] = df["toi_seconds"].apply(toi_to_seconds)
        # Compute save_pct if not present
        if "save_pct" not in df.columns:
            df["save_pct"] = df.apply(
                lambda row: row["saves"] / row["shots_against"]
                if row["shots_against"] > 0
                else None,
                axis=1,
            )
        df.to_csv(PROCESSED_DIR / f"{date_str}_goalie_stats.csv", index=False)
        result["fact_game_goalie_stats"] = df
        logger.info("Transformed %d goalie stat records", len(df))

    return result
