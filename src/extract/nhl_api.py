"""NHL API client for extracting game data, player stats, and standings.

Uses the public NHL web API (api-web.nhle.com). No authentication required.
"""

import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api-web.nhle.com/v1"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


class NHLAPIClient:
    """Client for the public NHL API."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.client = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "NHLAPIClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _get(self, endpoint: str) -> dict:
        """Make a GET request with retry logic."""
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.get(endpoint)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                last_exception = e
                wait = RETRY_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s. Retrying in %ds.",
                    endpoint,
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                    wait,
                )
                import time
                time.sleep(wait)

        raise last_exception  # type: ignore[misc]

    def get_schedule(self, game_date: date) -> dict:
        """Get the schedule for a specific date."""
        return self._get(f"/schedule/{game_date.isoformat()}")

    def get_scores(self, game_date: date) -> dict:
        """Get scores for a specific date."""
        return self._get(f"/score/{game_date.isoformat()}")

    def get_standings(self, game_date: date) -> dict:
        """Get league standings as of a specific date."""
        return self._get(f"/standings/{game_date.isoformat()}")

    def get_player(self, player_id: int) -> dict:
        """Get player landing page data."""
        return self._get(f"/player/{player_id}/landing")

    def get_player_game_log(self, player_id: int, season: str, game_type: int = 2) -> dict:
        """Get a player's game log for a season.

        Args:
            player_id: NHL player ID.
            season: Season string, e.g. "20242025".
            game_type: 2 for regular season, 3 for playoffs.
        """
        return self._get(f"/player/{player_id}/game-log/{season}/{game_type}")

    def get_game_boxscore(self, game_id: int) -> dict:
        """Get the boxscore for a specific game."""
        return self._get(f"/gamecenter/{game_id}/boxscore")

    def get_roster(self, team_abbrev: str, season: str) -> dict:
        """Get a team's roster for a season."""
        return self._get(f"/roster/{team_abbrev}/{season}")
