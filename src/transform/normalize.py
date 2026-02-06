"""Team and position normalization."""

from src.models.team import Team


def normalize_team(abbrev: str) -> str:
    """Normalize a team abbreviation to its canonical form."""
    return Team.normalize_abbrev(abbrev)


def normalize_position(position: str) -> str:
    """Normalize position codes.

    NHL API uses: C, L, R, D, G
    Standardize to: C, LW, RW, D, G
    """
    mapping = {
        "L": "LW",
        "R": "RW",
        "C": "C",
        "D": "D",
        "G": "G",
    }
    return mapping.get(position.upper(), position.upper())
