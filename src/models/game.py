from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Game:
    """An NHL game."""

    game_id: int
    season: str
    game_type: int  # 2 = regular season, 3 = playoffs
    game_date: date
    home_team_abbrev: str
    away_team_abbrev: str
    home_score: int | None = None
    away_score: int | None = None
    venue: str | None = None
    start_time_utc: datetime | None = None
    game_state: str | None = None  # "FUT", "LIVE", "OFF", "FINAL"

    @property
    def is_final(self) -> bool:
        return self.game_state in ("OFF", "FINAL")
