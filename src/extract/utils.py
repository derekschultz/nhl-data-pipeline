"""Utilities for data extraction: rate limiting, date ranges, etc."""

from datetime import date, timedelta


def date_range(start: date, end: date) -> list[date]:
    """Generate a list of dates from start to end (inclusive)."""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def current_season_string() -> str:
    """Return the current NHL season string (e.g., '20252026').

    The NHL season spans two calendar years. If we're before September,
    we're in the previous season.
    """
    today = date.today()
    if today.month >= 9:
        return f"{today.year}{today.year + 1}"
    return f"{today.year - 1}{today.year}"
