"""Data models for DFS slate analysis.

These represent the game environment classification that is the core
of the DFS research framework — game selection before player selection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass
class PlayerLine:
    """A player's slot within a line combination."""

    name: str
    position: str  # LW, C, RW, LD, RD, G
    injury_status: str | None = None  # "out", "dtd", None
    game_time_decision: bool = False


@dataclass
class LineCombination:
    """A single line/unit grouping (e.g., Forward Line 1, PP1)."""

    group_type: str  # "ev", "pp", "pk"
    group_name: str  # "Forwards 1", "1st Powerplay Unit", etc.
    group_id: str  # "f1", "d1", "pp1", "pk1", "g"
    players: list[PlayerLine] = field(default_factory=list)


@dataclass
class TeamLines:
    """Full line combination data for a single team."""

    team_abbrev: str
    forward_lines: list[LineCombination] = field(default_factory=list)  # f1-f4
    defense_pairs: list[LineCombination] = field(default_factory=list)  # d1-d3
    power_play: list[LineCombination] = field(default_factory=list)  # pp1-pp2
    penalty_kill: list[LineCombination] = field(default_factory=list)  # pk1-pk2
    starting_goalie: PlayerLine | None = None
    backup_goalie: PlayerLine | None = None


class GameEnvironment(StrEnum):
    """Game environment tier for DFS entry allocation.

    CHALK: High-total games with strong shot quality on both sides.
           Everyone will be here. You need exposure but not overweight.
           ~25% of entries.

    LEVERAGE: Moderate-to-high totals where one side has a shot quality
              edge the market may be underpricing. This is where edges live.
              ~50% of entries.

    CONTRARIAN: Low totals, bad shot quality, or trap games where
                Vegas disagrees with the underlying data. Thin ownership.
                ~25% of entries for GPP upside.

    AVOID: Games with no clear edge or path to differentiation.
    """

    CHALK = "chalk"
    LEVERAGE = "leverage"
    CONTRARIAN = "contrarian"
    AVOID = "avoid"


@dataclass
class GameOdds:
    """Vegas odds for a single game."""

    event_id: str
    home_team: str
    away_team: str
    commence_time: datetime | None
    home_ml: int
    away_ml: int
    home_spread: float | None
    total: float
    home_implied_total: float
    away_implied_total: float
    bookmaker: str = "draftkings"


@dataclass
class TeamShotQuality:
    """Team-level shot quality metrics from Natural Stat Trick.

    All metrics are at 5v5 unless otherwise noted.
    """

    team_abbrev: str
    games: int = 0
    cf_pct: float | None = None          # Corsi For %
    ff_pct: float | None = None          # Fenwick For %
    sf_pct: float | None = None          # Shots For %
    gf_pct: float | None = None          # Goals For %
    xgf_pct: float | None = None         # Expected Goals For %
    hdcf_pct: float | None = None        # High-Danger Corsi For %
    hdcf_per_60: float | None = None     # High-Danger Chances For per 60
    hdca_per_60: float | None = None     # High-Danger Chances Against per 60
    sh_pct: float | None = None          # Shooting %
    sv_pct: float | None = None          # Save %
    pdo: float | None = None             # PDO (shooting% + save%) — luck indicator


@dataclass
class GameSlateEntry:
    """A single game's full slate analysis — the core unit of the product.

    Combines Vegas odds + shot quality for both teams + environment classification.
    """

    # Game identity
    home_team: str
    away_team: str
    commence_time: datetime | None = None

    # Vegas
    total: float = 0.0
    home_implied_total: float = 0.0
    away_implied_total: float = 0.0
    home_ml: int = 0
    away_ml: int = 0
    home_spread: float | None = None

    # Home team shot quality
    home_hdcf_pct: float | None = None
    home_xgf_pct: float | None = None
    home_hdcf_per_60: float | None = None
    home_hdca_per_60: float | None = None
    home_pdo: float | None = None

    # Away team shot quality
    away_hdcf_pct: float | None = None
    away_xgf_pct: float | None = None
    away_hdcf_per_60: float | None = None
    away_hdca_per_60: float | None = None
    away_pdo: float | None = None

    # Classification
    environment: GameEnvironment = GameEnvironment.AVOID
    environment_reason: str = ""

    # Flags
    divergence_flag: bool = False
    divergence_detail: str = ""

    # Line combinations (from DailyFaceoff)
    home_lines: TeamLines | None = None
    away_lines: TeamLines | None = None

    @property
    def matchup(self) -> str:
        return f"{away_team} @ {home_team}" if (
            away_team := self.away_team
        ) and (home_team := self.home_team) else ""

    @property
    def is_high_total(self) -> bool:
        return self.total >= 6.0

    @property
    def is_moderate_total(self) -> bool:
        return 5.5 <= self.total < 6.0


@dataclass
class SlateBreakdown:
    """Full slate analysis for a given day — the top-level product output."""

    games: list[GameSlateEntry] = field(default_factory=list)

    @property
    def chalk_games(self) -> list[GameSlateEntry]:
        return [g for g in self.games if g.environment == GameEnvironment.CHALK]

    @property
    def leverage_games(self) -> list[GameSlateEntry]:
        return [g for g in self.games if g.environment == GameEnvironment.LEVERAGE]

    @property
    def contrarian_games(self) -> list[GameSlateEntry]:
        return [g for g in self.games if g.environment == GameEnvironment.CONTRARIAN]

    @property
    def avoid_games(self) -> list[GameSlateEntry]:
        return [g for g in self.games if g.environment == GameEnvironment.AVOID]

    @property
    def divergence_games(self) -> list[GameSlateEntry]:
        return [g for g in self.games if g.divergence_flag]
