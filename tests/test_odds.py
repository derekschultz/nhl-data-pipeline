"""Tests for the odds API client and parsing."""

from src.extract.odds_api import _ml_to_implied_prob, parse_game_odds


class TestMLToImpliedProb:
    def test_heavy_favorite(self) -> None:
        # -200 → 66.67%
        prob = _ml_to_implied_prob(-200)
        assert abs(prob - 0.6667) < 0.001

    def test_underdog(self) -> None:
        # +150 → 40.00%
        prob = _ml_to_implied_prob(150)
        assert abs(prob - 0.4000) < 0.001

    def test_even_money(self) -> None:
        # +100 → 50.00%
        prob = _ml_to_implied_prob(100)
        assert abs(prob - 0.5000) < 0.001

    def test_slight_favorite(self) -> None:
        # -110 → 52.38%
        prob = _ml_to_implied_prob(-110)
        assert abs(prob - 0.5238) < 0.001


class TestParseGameOdds:
    def test_parses_complete_event(self) -> None:
        event = {
            "id": "abc123",
            "home_team": "Colorado Avalanche",
            "away_team": "Edmonton Oilers",
            "commence_time": "2026-02-23T02:00:00Z",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Colorado Avalanche", "price": -150},
                                {"name": "Edmonton Oilers", "price": 130},
                            ],
                        },
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Colorado Avalanche", "price": -120, "point": -1.5},
                                {"name": "Edmonton Oilers", "price": 100, "point": 1.5},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": -110, "point": 6.5},
                                {"name": "Under", "price": -110, "point": 6.5},
                            ],
                        },
                    ],
                }
            ],
        }

        result = parse_game_odds(event)
        assert result is not None
        assert result["home_team"] == "Colorado Avalanche"
        assert result["away_team"] == "Edmonton Oilers"
        assert result["total"] == 6.5
        assert result["home_ml"] == -150
        assert result["away_ml"] == 130
        assert result["home_spread"] == -1.5
        # Implied totals: home favorite gets larger share
        assert result["home_implied_total"] > result["away_implied_total"]
        assert abs(result["home_implied_total"] + result["away_implied_total"] - 6.5) < 0.01

    def test_returns_none_for_empty_bookmakers(self) -> None:
        event = {
            "id": "abc123",
            "home_team": "Team A",
            "away_team": "Team B",
            "bookmakers": [],
        }
        assert parse_game_odds(event) is None

    def test_returns_none_for_missing_totals(self) -> None:
        event = {
            "id": "abc123",
            "home_team": "Team A",
            "away_team": "Team B",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Team A", "price": -150},
                                {"name": "Team B", "price": 130},
                            ],
                        },
                    ],
                }
            ],
        }
        assert parse_game_odds(event) is None
