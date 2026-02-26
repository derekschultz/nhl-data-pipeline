"""Tests for the game environment classifier."""

from src.analysis.game_environment import classify_game
from src.models.slate import GameEnvironment, GameOdds, TeamShotQuality


def _make_odds(
    total: float = 6.0,
    home_ml: int = -150,
    away_ml: int = 130,
) -> GameOdds:
    """Create a test GameOdds."""
    return GameOdds(
        event_id="test",
        home_team="Home Team",
        away_team="Away Team",
        commence_time=None,
        home_ml=home_ml,
        away_ml=away_ml,
        home_spread=-1.5,
        total=total,
        home_implied_total=total * 0.55,
        away_implied_total=total * 0.45,
        bookmaker="test",
    )


def _make_quality(
    abbrev: str = "TST",
    hdcf_pct: float = 50.0,
    xgf_pct: float = 50.0,
    pdo: float = 100.0,
) -> TeamShotQuality:
    """Create a test TeamShotQuality."""
    return TeamShotQuality(
        team_abbrev=abbrev,
        games=50,
        hdcf_pct=hdcf_pct,
        xgf_pct=xgf_pct,
        pdo=pdo,
    )


class TestClassifyChalk:
    def test_high_total_strong_both_sides(self) -> None:
        odds = _make_odds(total=6.5)
        home_q = _make_quality(hdcf_pct=54.0, xgf_pct=53.0)
        away_q = _make_quality(hdcf_pct=53.0, xgf_pct=52.0)

        result = classify_game(odds, home_q, away_q)
        assert result.environment == GameEnvironment.CHALK

    def test_high_total_no_quality_data(self) -> None:
        odds = _make_odds(total=6.5)
        result = classify_game(odds, None, None)
        assert result.environment == GameEnvironment.CHALK


class TestClassifyLeverage:
    def test_moderate_total_one_side_dominant(self) -> None:
        odds = _make_odds(total=5.5)
        home_q = _make_quality(hdcf_pct=55.0)
        away_q = _make_quality(hdcf_pct=44.0)

        result = classify_game(odds, home_q, away_q)
        assert result.environment == GameEnvironment.LEVERAGE
        assert "dominating" in result.environment_reason.lower()

    def test_moderate_total_away_dominant(self) -> None:
        odds = _make_odds(total=5.5)
        home_q = _make_quality(hdcf_pct=44.0)
        away_q = _make_quality(hdcf_pct=55.0)

        result = classify_game(odds, home_q, away_q)
        assert result.environment == GameEnvironment.LEVERAGE


class TestClassifyContrarian:
    def test_low_total_one_strong_team(self) -> None:
        odds = _make_odds(total=5.0)
        home_q = _make_quality(hdcf_pct=54.0)
        away_q = _make_quality(hdcf_pct=44.0)

        result = classify_game(odds, home_q, away_q)
        assert result.environment == GameEnvironment.CONTRARIAN

    def test_low_total_no_quality_data(self) -> None:
        odds = _make_odds(total=5.0)
        result = classify_game(odds, None, None)
        assert result.environment == GameEnvironment.CONTRARIAN


class TestClassifyAvoid:
    def test_low_total_weak_both_sides(self) -> None:
        odds = _make_odds(total=5.0)
        home_q = _make_quality(hdcf_pct=46.0)
        away_q = _make_quality(hdcf_pct=45.0)

        result = classify_game(odds, home_q, away_q)
        assert result.environment == GameEnvironment.AVOID


class TestDivergenceDetection:
    def test_high_implied_total_low_hdcf(self) -> None:
        odds = _make_odds(total=6.0)
        # Override implied totals for clear divergence
        odds.home_implied_total = 3.5
        home_q = _make_quality(hdcf_pct=44.0)
        away_q = _make_quality(hdcf_pct=52.0)

        result = classify_game(odds, home_q, away_q)
        assert result.divergence_flag
        assert "overpricing" in result.divergence_detail.lower()

    def test_high_pdo_flagged(self) -> None:
        odds = _make_odds(total=6.0)
        home_q = _make_quality(hdcf_pct=53.0, pdo=103.0)
        away_q = _make_quality(hdcf_pct=53.0, pdo=99.0)

        result = classify_game(odds, home_q, away_q)
        assert result.divergence_flag
        assert "pdo" in result.divergence_detail.lower()

    def test_no_divergence_when_quality_matches_total(self) -> None:
        odds = _make_odds(total=6.0)
        home_q = _make_quality(hdcf_pct=54.0, pdo=100.0)
        away_q = _make_quality(hdcf_pct=53.0, pdo=100.0)

        result = classify_game(odds, home_q, away_q)
        assert not result.divergence_flag
