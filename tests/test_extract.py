"""Tests for the extract layer."""

from datetime import date

from src.extract.utils import current_season_string, date_range


class TestDateRange:
    def test_single_day(self) -> None:
        result = date_range(date(2026, 1, 1), date(2026, 1, 1))
        assert result == [date(2026, 1, 1)]

    def test_multiple_days(self) -> None:
        result = date_range(date(2026, 1, 1), date(2026, 1, 3))
        assert result == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    def test_empty_range(self) -> None:
        result = date_range(date(2026, 1, 3), date(2026, 1, 1))
        assert result == []


class TestCurrentSeasonString:
    def test_returns_string_format(self) -> None:
        season = current_season_string()
        assert len(season) == 8
        assert season.isdigit()
