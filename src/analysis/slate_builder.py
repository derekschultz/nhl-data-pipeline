"""Slate builder — orchestrates fetching odds + shot quality and building the breakdown.

This is the glue between data sources and the game environment classifier.
Call build_tonight_slate() to get a full SlateBreakdown ready for the dashboard.
"""

import logging
from datetime import datetime

from src.analysis.game_environment import build_slate_breakdown
from src.extract.natural_stat_trick import (
    ODDS_API_NAME_TO_ABBREV,
    fetch_team_shot_quality,
)
from src.extract.odds_api import OddsAPIClient, parse_game_odds
from src.models.slate import GameOdds, SlateBreakdown, TeamShotQuality

logger = logging.getLogger(__name__)


def build_tonight_slate(
    odds_api_key: str | None = None,
    bookmaker: str = "draftkings",
) -> SlateBreakdown:
    """Build a full slate breakdown for tonight's games.

    Fetches Vegas odds from The Odds API and shot quality from Natural Stat Trick,
    then classifies each game environment.

    Args:
        odds_api_key: The Odds API key. Falls back to ODDS_API_KEY env var.
        bookmaker: Which bookmaker to use for odds (default 'draftkings').

    Returns:
        SlateBreakdown with all games classified.
    """
    # 1. Fetch odds
    logger.info("Fetching tonight's odds...")
    odds_list = fetch_odds(odds_api_key, bookmaker)
    logger.info("Got odds for %d games", len(odds_list))

    if not odds_list:
        logger.warning("No games found — is there an NHL slate today?")
        return SlateBreakdown(games=[])

    # 2. Fetch shot quality
    logger.info("Fetching team shot quality from Natural Stat Trick...")
    shot_quality = fetch_shot_quality()
    logger.info("Got shot quality for %d team entries", len(shot_quality))

    # 3. Classify environments
    slate = build_slate_breakdown(odds_list, shot_quality)
    logger.info(
        "Slate breakdown: %d chalk, %d leverage, %d contrarian, %d avoid",
        len(slate.chalk_games),
        len(slate.leverage_games),
        len(slate.contrarian_games),
        len(slate.avoid_games),
    )

    return slate


def fetch_odds(
    api_key: str | None = None,
    bookmaker: str = "draftkings",
) -> list[GameOdds]:
    """Fetch and parse odds for all upcoming NHL games."""
    with OddsAPIClient(api_key=api_key) as client:
        raw_events = client.get_nhl_odds(bookmakers=bookmaker)

    odds_list: list[GameOdds] = []
    for event in raw_events:
        parsed = parse_game_odds(event)
        if parsed is None:
            continue

        commence_time = None
        if parsed["commence_time"]:
            try:
                commence_time = datetime.fromisoformat(
                    parsed["commence_time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        odds = GameOdds(
            event_id=parsed["event_id"],
            home_team=parsed["home_team"],
            away_team=parsed["away_team"],
            commence_time=commence_time,
            home_ml=parsed["home_ml"],
            away_ml=parsed["away_ml"],
            home_spread=parsed["home_spread"],
            total=parsed["total"],
            home_implied_total=parsed["home_implied_total"],
            away_implied_total=parsed["away_implied_total"],
            bookmaker=parsed["bookmaker"],
        )
        odds_list.append(odds)

    return odds_list


def fetch_shot_quality(last_n_games: int = 10) -> dict[str, TeamShotQuality]:
    """Fetch team shot quality from Natural Stat Trick.

    Defaults to last 10 games — recent form is more relevant for DFS
    than full-season averages.

    Returns dict keyed by BOTH team abbreviation and full team name
    for flexible matching with Odds API team names.
    """
    quality = fetch_team_shot_quality(last_n_games=last_n_games)

    # Also add Odds API name mappings so the classifier can find teams
    extra_mappings: dict[str, TeamShotQuality] = {}
    for full_name, abbrev in ODDS_API_NAME_TO_ABBREV.items():
        if abbrev in quality and full_name not in quality:
            extra_mappings[full_name] = quality[abbrev]

    quality.update(extra_mappings)
    return quality
