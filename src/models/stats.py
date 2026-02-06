from dataclasses import dataclass


@dataclass
class SkaterGameStats:
    """Per-game statistics for a skater."""

    player_id: int
    game_id: int
    team_abbrev: str
    goals: int = 0
    assists: int = 0
    points: int = 0
    shots: int = 0
    hits: int = 0
    blocked_shots: int = 0
    pim: int = 0
    toi_seconds: int = 0
    plus_minus: int = 0
    power_play_goals: int = 0
    power_play_points: int = 0
    shorthanded_goals: int = 0
    faceoff_pct: float | None = None

    @property
    def toi_minutes(self) -> float:
        return self.toi_seconds / 60.0


@dataclass
class GoalieGameStats:
    """Per-game statistics for a goalie."""

    player_id: int
    game_id: int
    team_abbrev: str
    decision: str | None = None  # "W", "L", "O"
    shots_against: int = 0
    saves: int = 0
    goals_against: int = 0
    toi_seconds: int = 0
    power_play_saves: int = 0
    shorthanded_saves: int = 0
    even_strength_saves: int = 0

    @property
    def save_pct(self) -> float | None:
        if self.shots_against == 0:
            return None
        return self.saves / self.shots_against

    @property
    def toi_minutes(self) -> float:
        return self.toi_seconds / 60.0
