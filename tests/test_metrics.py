"""Tests for the rolling average metrics module."""

import pandas as pd

from src.transform.metrics import add_rolling_averages


class TestRollingAverages:
    """Test add_rolling_averages with various scenarios."""

    def test_basic_rolling_window(self) -> None:
        """Rolling average computed correctly over a 3-game window."""
        df = pd.DataFrame({
            "player_id": [1] * 5,
            "game_date": pd.date_range("2026-01-01", periods=5),
            "goals": [2, 4, 6, 8, 10],
        })
        result = add_rolling_averages(df, ["goals"], window=3)
        # Game 1: avg(2) = 2.0
        # Game 2: avg(2,4) = 3.0
        # Game 3: avg(2,4,6) = 4.0
        # Game 4: avg(4,6,8) = 6.0
        # Game 5: avg(6,8,10) = 8.0
        expected = [2.0, 3.0, 4.0, 6.0, 8.0]
        assert result["goals_rolling_3"].tolist() == expected

    def test_min_periods_one(self) -> None:
        """Players with fewer games than the window still get averages."""
        df = pd.DataFrame({
            "player_id": [1, 1],
            "game_date": pd.date_range("2026-01-01", periods=2),
            "shots": [10, 20],
        })
        result = add_rolling_averages(df, ["shots"], window=10)
        assert result["shots_rolling_10"].tolist() == [10.0, 15.0]

    def test_multiple_players_grouped(self) -> None:
        """Each player's rolling average is computed independently."""
        df = pd.DataFrame({
            "player_id": [1, 1, 1, 2, 2, 2],
            "game_date": pd.date_range("2026-01-01", periods=3).tolist() * 2,
            "goals": [1, 2, 3, 10, 20, 30],
        })
        result = add_rolling_averages(df, ["goals"], window=2)
        # Player 1: [1.0, 1.5, 2.5]
        # Player 2: [10.0, 15.0, 25.0]
        p1 = result[result["player_id"] == 1]["goals_rolling_2"].tolist()
        p2 = result[result["player_id"] == 2]["goals_rolling_2"].tolist()
        assert p1 == [1.0, 1.5, 2.5]
        assert p2 == [10.0, 15.0, 25.0]

    def test_multiple_stat_columns(self) -> None:
        """Rolling averages computed for multiple stats at once."""
        df = pd.DataFrame({
            "player_id": [1, 1, 1],
            "game_date": pd.date_range("2026-01-01", periods=3),
            "goals": [1, 2, 3],
            "assists": [4, 5, 6],
        })
        result = add_rolling_averages(df, ["goals", "assists"], window=2)
        assert "goals_rolling_2" in result.columns
        assert "assists_rolling_2" in result.columns
        assert result["goals_rolling_2"].tolist() == [1.0, 1.5, 2.5]
        assert result["assists_rolling_2"].tolist() == [4.0, 4.5, 5.5]

    def test_unsorted_input_gets_sorted(self) -> None:
        """Function sorts by player_id and game_date even if input is unsorted."""
        df = pd.DataFrame({
            "player_id": [1, 1, 1],
            "game_date": ["2026-01-03", "2026-01-01", "2026-01-02"],
            "goals": [30, 10, 20],
        })
        result = add_rolling_averages(df, ["goals"], window=3)
        # After sorting: 10, 20, 30 → rolling: 10, 15, 20
        rolling = result.sort_values("game_date")["goals_rolling_3"].tolist()
        assert rolling == [10.0, 15.0, 20.0]

    def test_nan_values_handled(self) -> None:
        """NaN values in stat columns are skipped by rolling mean."""
        df = pd.DataFrame({
            "player_id": [1, 1, 1],
            "game_date": pd.date_range("2026-01-01", periods=3),
            "faceoff_pct": [50.0, None, 60.0],
        })
        result = add_rolling_averages(df, ["faceoff_pct"], window=3)
        rolling = result["faceoff_pct_rolling_3"].tolist()
        assert rolling[0] == 50.0
        # Game 2: avg(50, NaN) = 50.0 (NaN skipped)
        assert rolling[1] == 50.0
        # Game 3: avg(50, NaN, 60) = 55.0
        assert rolling[2] == 55.0
