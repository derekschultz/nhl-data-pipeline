"""Scraper for Natural Stat Trick team-level shot quality data.

Natural Stat Trick provides free, public team-level analytics including:
- HDCF% (High-Danger Corsi For %) — % of high-danger chances belonging to the team
- xGF% (Expected Goals For %) — expected goals share
- CF% (Corsi For %) — shot attempt share
- PDO (shooting% + save%) — luck/regression indicator

URL structure:
    https://www.naturalstattrick.com/teamtable.php
        ?fromseason=20252026&thruseason=20252026
        &stype=2          (2=regular season, 3=playoffs)
        &sit=5v5          (5v5, all, pp, pk)
        &score=all        (all, leading, trailing, close, etc.)
        &rate=n           (n=totals, y=per-60 rates)
        &team=all
        &loc=B            (B=both, H=home, A=away)
        &fd=&td=          (date filters, blank=full season)
"""

import logging
from datetime import date
from io import StringIO

import httpx
import pandas as pd

from src.models.slate import TeamShotQuality

logger = logging.getLogger(__name__)

BASE_URL = "https://www.naturalstattrick.com/teamtable.php"

# Map full team names (as NST uses them) to abbreviations
TEAM_NAME_TO_ABBREV: dict[str, str] = {
    "Anaheim Ducks": "ANA",
    "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF",
    "Carolina Hurricanes": "CAR",
    "Columbus Blue Jackets": "CBJ",
    "Calgary Flames": "CGY",
    "Chicago Blackhawks": "CHI",
    "Colorado Avalanche": "COL",
    "Dallas Stars": "DAL",
    "Detroit Red Wings": "DET",
    "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA",
    "Los Angeles Kings": "LAK",
    "Minnesota Wild": "MIN",
    "Montréal Canadiens": "MTL",
    "Montreal Canadiens": "MTL",
    "New Jersey Devils": "NJD",
    "Nashville Predators": "NSH",
    "New York Islanders": "NYI",
    "New York Rangers": "NYR",
    "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI",
    "Pittsburgh Penguins": "PIT",
    "Seattle Kraken": "SEA",
    "San Jose Sharks": "SJS",
    "St. Louis Blues": "STL",
    "St Louis Blues": "STL",
    "Tampa Bay Lightning": "TBL",
    "Toronto Maple Leafs": "TOR",
    "Utah Mammoth": "UTA",
    "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK",
    "Winnipeg Jets": "WPG",
    "Washington Capitals": "WSH",
}

# Also map full names used by The Odds API to abbreviations
# (Odds API may use slightly different names)
ODDS_API_NAME_TO_ABBREV: dict[str, str] = {
    **TEAM_NAME_TO_ABBREV,
    "Arizona Coyotes": "UTA",
}


def _current_season() -> str:
    """Return current NHL season string (e.g., '20252026')."""
    today = date.today()
    if today.month >= 9:
        return f"{today.year}{today.year + 1}"
    return f"{today.year - 1}{today.year}"


def fetch_team_shot_quality(
    season: str | None = None,
    situation: str = "5v5",
    last_n_games: int | None = None,
    from_date: str = "",
    thru_date: str = "",
) -> dict[str, TeamShotQuality]:
    """Fetch team-level shot quality data from Natural Stat Trick.

    Args:
        season: Season string like '20252026'. Defaults to current season.
        situation: Game situation filter ('5v5', 'all', 'ev', 'pp', 'pk').
        last_n_games: If set, fetch only the last N games per team (e.g., 10, 25).
                      More relevant for DFS than full-season data.
        from_date: Start date filter 'YYYY-MM-DD' (only when last_n_games is None).
        thru_date: End date filter 'YYYY-MM-DD' (only when last_n_games is None).

    Returns:
        Dict of team abbreviation → TeamShotQuality.
    """
    if season is None:
        season = _current_season()

    # Game filter: last N games or date range or full season
    if last_n_games is not None:
        gpfilt = "gpteam"
        tgp = str(last_n_games)
    elif from_date or thru_date:
        gpfilt = "gpdate"
        tgp = "82"
    else:
        gpfilt = "none"
        tgp = "82"

    params = {
        "fromseason": season,
        "thruseason": season,
        "stype": "2",
        "sit": situation,
        "score": "all",
        "rate": "n",
        "team": "all",
        "loc": "B",
        "gpfilt": gpfilt,
        "tgp": tgp,
        "fd": from_date,
        "td": thru_date,
    }

    window_desc = (
        f"last {last_n_games} games" if last_n_games
        else f"{from_date or 'season start'} to {thru_date or 'today'}"
    )
    logger.info(
        "Fetching Natural Stat Trick team data: season=%s, sit=%s, window=%s",
        season,
        situation,
        window_desc,
    )

    response = httpx.get(
        BASE_URL,
        params=params,
        timeout=30.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; NHLDataPipeline/1.0; "
                "personal research tool)"
            ),
        },
    )
    response.raise_for_status()

    # Parse the HTML table with pandas
    tables = pd.read_html(StringIO(response.text))
    if not tables:
        logger.warning("No tables found on Natural Stat Trick page")
        return {}

    # The main team stats table is the first (and usually only) one
    df = tables[0]
    logger.info("Parsed %d teams from Natural Stat Trick", len(df))

    return _dataframe_to_shot_quality(df)


def _dataframe_to_shot_quality(df: pd.DataFrame) -> dict[str, TeamShotQuality]:
    """Convert Natural Stat Trick DataFrame to TeamShotQuality dict."""
    result: dict[str, TeamShotQuality] = {}

    for _, row in df.iterrows():
        team_name = str(row.get("Team", "")).strip()
        if not team_name:
            continue

        abbrev = TEAM_NAME_TO_ABBREV.get(team_name)
        if not abbrev:
            logger.warning("Unknown team name from NST: %s", team_name)
            continue

        quality = TeamShotQuality(
            team_abbrev=abbrev,
            games=_safe_int(row, "GP"),
            cf_pct=_safe_float(row, "CF%"),
            ff_pct=_safe_float(row, "FF%"),
            sf_pct=_safe_float(row, "SF%"),
            gf_pct=_safe_float(row, "GF%"),
            xgf_pct=_safe_float(row, "xGF%"),
            hdcf_pct=_safe_float(row, "HDCF%"),
            hdcf_per_60=_safe_float(row, "HDCF"),  # Raw count; per-60 if rate=y
            hdca_per_60=_safe_float(row, "HDCA"),
            sh_pct=_safe_float(row, "SH%"),
            sv_pct=_safe_float(row, "SV%"),
            pdo=_safe_float(row, "PDO"),
        )

        # Store by abbreviation AND full name for flexible lookups
        result[abbrev] = quality
        result[team_name] = quality

    logger.info("Processed shot quality for %d unique teams", len(df))
    return result


def team_name_to_abbrev(name: str) -> str | None:
    """Convert a full team name to its abbreviation.

    Handles both Natural Stat Trick and Odds API name formats.
    """
    return ODDS_API_NAME_TO_ABBREV.get(name)


def _safe_float(row: pd.Series, col: str) -> float | None:
    """Safely extract a float from a DataFrame row."""
    try:
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(row: pd.Series, col: str) -> int:
    """Safely extract an int from a DataFrame row."""
    try:
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0
        return int(val)
    except (ValueError, TypeError):
        return 0
