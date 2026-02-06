from dataclasses import dataclass


@dataclass
class Player:
    """An NHL player."""

    player_id: int
    first_name: str
    last_name: str
    position: str
    team_abbrev: str
    jersey_number: int | None = None
    shoots_catches: str | None = None
    birth_date: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
