"""Client for The Odds API — fetches NHL game odds (totals, spreads, moneylines).

Free tier: 500 credits/month. Fetching h2h+spreads+totals = 3 credits per call.
One call per day for tonight's slate is ~90 credits/month — well within budget.

API docs: https://the-odds-api.com/liveapi/guides/v4/
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "icehockey_nhl"


class OddsAPIClient:
    """Client for The Odds API."""

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key or os.environ.get("ODDS_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "ODDS_API_KEY is required. Get a free key at https://the-odds-api.com"
            )
        self.client = httpx.Client(base_url=BASE_URL, timeout=timeout)
        self.credits_remaining: int | None = None
        self.credits_used: int | None = None

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "OddsAPIClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _get(self, endpoint: str, params: dict[str, str] | None = None) -> object:
        """Make a GET request, track credit usage."""
        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        response = self.client.get(endpoint, params=params)
        response.raise_for_status()

        # Track quota from response headers
        self.credits_remaining = _parse_int_header(response, "x-requests-remaining")
        self.credits_used = _parse_int_header(response, "x-requests-used")
        last_cost = _parse_int_header(response, "x-requests-last")

        logger.info(
            "Odds API: %s — cost %s credits, %s remaining",
            endpoint,
            last_cost,
            self.credits_remaining,
        )

        return response.json()  # type: ignore[no-any-return]

    def get_nhl_odds(
        self,
        bookmakers: str | None = "draftkings",
    ) -> list[dict]:
        """Fetch odds for all upcoming/live NHL games.

        Returns h2h (moneyline), spreads (puck line), and totals (over/under)
        from the specified bookmaker(s).

        Args:
            bookmakers: Comma-separated bookmaker keys. Default 'draftkings'.
                        Use None for all available bookmakers.

        Returns:
            List of event dicts with nested bookmaker/market data.
        """
        params: dict[str, str] = {
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
        }
        if bookmakers:
            params["bookmakers"] = bookmakers

        result = self._get(f"/sports/{SPORT_KEY}/odds", params)
        if not isinstance(result, list):
            return []
        return result

    def get_nhl_events(self) -> list[dict]:
        """List upcoming/live NHL events (free — no credit cost).

        Returns:
            List of event dicts with id, home_team, away_team, commence_time.
        """
        result = self._get(f"/sports/{SPORT_KEY}/events")
        if not isinstance(result, list):
            return []
        return result


def _parse_int_header(response: httpx.Response, header: str) -> int | None:
    """Parse an integer from a response header, or None if missing."""
    val = response.headers.get(header)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def parse_game_odds(event: dict) -> dict | None:
    """Parse a single event from the odds response into a flat dict.

    Extracts the first bookmaker's h2h, spreads, and totals markets and
    computes implied team totals from moneyline probabilities.

    Returns:
        Dict with keys: event_id, home_team, away_team, commence_time,
        home_ml, away_ml, home_spread, total, home_implied_total,
        away_implied_total, bookmaker. Or None if data is incomplete.
    """
    bookmakers = event.get("bookmakers", [])
    if not bookmakers:
        return None

    book = bookmakers[0]
    markets = {m["key"]: m for m in book.get("markets", [])}

    h2h = markets.get("h2h")
    spreads = markets.get("spreads")
    totals = markets.get("totals")

    if h2h is None or totals is None:
        return None

    home_team = event["home_team"]
    away_team = event["away_team"]

    # Moneyline
    home_ml: int | None = None
    away_ml: int | None = None
    for outcome in h2h["outcomes"]:
        if outcome["name"] == home_team:
            home_ml = outcome["price"]
        elif outcome["name"] == away_team:
            away_ml = outcome["price"]

    # Game total
    total: float | None = None
    for outcome in totals["outcomes"]:
        if outcome["name"] == "Over":
            total = outcome["point"]
            break

    # Spread (puck line)
    home_spread: float | None = None
    if spreads:
        for outcome in spreads["outcomes"]:
            if outcome["name"] == home_team:
                home_spread = outcome["point"]
                break

    if total is None or home_ml is None or away_ml is None:
        return None

    # Compute implied team totals from moneyline probabilities
    home_prob = _ml_to_implied_prob(home_ml)
    away_prob = _ml_to_implied_prob(away_ml)

    # Remove vig by normalizing
    total_prob = home_prob + away_prob
    home_no_vig = home_prob / total_prob
    away_no_vig = away_prob / total_prob

    # Implied team totals = share of game total weighted by win probability
    # This is a standard DFS community approximation
    home_implied_total = round(total * home_no_vig, 2)
    away_implied_total = round(total * away_no_vig, 2)

    return {
        "event_id": event["id"],
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": event.get("commence_time"),
        "home_ml": home_ml,
        "away_ml": away_ml,
        "home_spread": home_spread,
        "total": total,
        "home_implied_total": home_implied_total,
        "away_implied_total": away_implied_total,
        "bookmaker": book["key"],
    }


def _ml_to_implied_prob(ml: int) -> float:
    """Convert American odds to implied probability (with vig included).

    Examples:
        -200 → 0.6667 (66.67%)
        +150 → 0.4000 (40.00%)
    """
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    else:
        return 100 / (ml + 100)
