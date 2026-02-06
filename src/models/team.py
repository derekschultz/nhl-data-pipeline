from dataclasses import dataclass

# Canonical abbreviations for all 32 NHL teams
TEAM_ABBREVIATIONS: dict[str, str] = {
    "ANA": "ANA", "BOS": "BOS", "BUF": "BUF", "CAR": "CAR",
    "CBJ": "CBJ", "CGY": "CGY", "CHI": "CHI", "COL": "COL",
    "DAL": "DAL", "DET": "DET", "EDM": "EDM", "FLA": "FLA",
    "LAK": "LAK", "MIN": "MIN", "MTL": "MTL", "NJD": "NJD",
    "NSH": "NSH", "NYI": "NYI", "NYR": "NYR", "OTT": "OTT",
    "PHI": "PHI", "PIT": "PIT", "SEA": "SEA", "SJS": "SJS",
    "STL": "STL", "TBL": "TBL", "TOR": "TOR", "UTA": "UTA",
    "VAN": "VAN", "VGK": "VGK", "WPG": "WPG", "WSH": "WSH",
    # Common alternates / relocated teams
    "ARI": "UTA", "MON": "MTL", "NAS": "NSH", "SJ": "SJS",
    "TB": "TBL", "LA": "LAK", "NJ": "NJD", "WAS": "WSH",
    "VEG": "VGK", "CLB": "CBJ", "CAL": "CGY",
}


@dataclass
class Team:
    """An NHL team."""

    abbrev: str
    full_name: str
    division: str
    conference: str

    @staticmethod
    def normalize_abbrev(abbrev: str) -> str:
        """Normalize a team abbreviation to its canonical form."""
        return TEAM_ABBREVIATIONS.get(abbrev.upper(), abbrev.upper())
