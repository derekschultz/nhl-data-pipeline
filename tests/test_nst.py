"""Tests for Natural Stat Trick team name mappings."""

from src.extract.natural_stat_trick import (
    ODDS_API_NAME_TO_ABBREV,
    TEAM_NAME_TO_ABBREV,
    team_name_to_abbrev,
)


class TestTeamNameMapping:
    """Verify all 32 NHL teams map correctly."""

    EXPECTED_TEAMS = {
        "Anaheim Ducks": "ANA",
        "Boston Bruins": "BOS",
        "Buffalo Sabres": "BUF",
        "Carolina Hurricanes": "CAR",
        "Columbus Blue Jackets": "CBJ",
        "Calgary Flames": "CGY",
        "Chicago Blackhawks": "CHI",
        "Colorado Avalanche": "COL",
        "Dallas Stars": "DAL",
        "Detroit Red Wings": "DET",
        "Edmonton Oilers": "EDM",
        "Florida Panthers": "FLA",
        "Los Angeles Kings": "LAK",
        "Minnesota Wild": "MIN",
        "New Jersey Devils": "NJD",
        "Nashville Predators": "NSH",
        "New York Islanders": "NYI",
        "New York Rangers": "NYR",
        "Ottawa Senators": "OTT",
        "Philadelphia Flyers": "PHI",
        "Pittsburgh Penguins": "PIT",
        "Seattle Kraken": "SEA",
        "San Jose Sharks": "SJS",
        "St. Louis Blues": "STL",
        "Tampa Bay Lightning": "TBL",
        "Toronto Maple Leafs": "TOR",
        "Utah Mammoth": "UTA",
        "Vancouver Canucks": "VAN",
        "Vegas Golden Knights": "VGK",
        "Winnipeg Jets": "WPG",
        "Washington Capitals": "WSH",
    }

    def test_all_32_teams_mapped(self) -> None:
        """TEAM_NAME_TO_ABBREV covers all 32 current NHL teams."""
        abbrevs = {v for v in TEAM_NAME_TO_ABBREV.values()}
        assert len(abbrevs) == 32

    def test_expected_mappings(self) -> None:
        """Each expected team name maps to the correct abbreviation."""
        for name, expected_abbrev in self.EXPECTED_TEAMS.items():
            assert TEAM_NAME_TO_ABBREV[name] == expected_abbrev, (
                f"{name} should map to {expected_abbrev}"
            )

    def test_utah_mammoth_replaces_hockey_club(self) -> None:
        """Utah Mammoth is the current mapping; Utah Hockey Club is removed."""
        assert "Utah Mammoth" in TEAM_NAME_TO_ABBREV
        assert "Utah Hockey Club" not in TEAM_NAME_TO_ABBREV

    def test_st_louis_variants(self) -> None:
        """Both 'St. Louis' and 'St Louis' (no period) map to STL."""
        assert TEAM_NAME_TO_ABBREV["St. Louis Blues"] == "STL"
        assert TEAM_NAME_TO_ABBREV["St Louis Blues"] == "STL"

    def test_montreal_variants(self) -> None:
        """Both accented and unaccented Montreal map to MTL."""
        assert TEAM_NAME_TO_ABBREV["Montréal Canadiens"] == "MTL"
        assert TEAM_NAME_TO_ABBREV["Montreal Canadiens"] == "MTL"


class TestOddsApiNameMapping:
    """Verify Odds API name overrides work correctly."""

    def test_arizona_coyotes_maps_to_utah(self) -> None:
        """Arizona Coyotes (legacy Odds API name) maps to UTA."""
        assert ODDS_API_NAME_TO_ABBREV["Arizona Coyotes"] == "UTA"

    def test_inherits_all_nst_mappings(self) -> None:
        """ODDS_API_NAME_TO_ABBREV includes all NST mappings."""
        for name, abbrev in TEAM_NAME_TO_ABBREV.items():
            assert ODDS_API_NAME_TO_ABBREV[name] == abbrev


class TestTeamNameToAbbrev:
    """Test the team_name_to_abbrev() helper function."""

    def test_known_team(self) -> None:
        assert team_name_to_abbrev("Colorado Avalanche") == "COL"

    def test_odds_api_legacy_name(self) -> None:
        assert team_name_to_abbrev("Arizona Coyotes") == "UTA"

    def test_unknown_team_returns_none(self) -> None:
        assert team_name_to_abbrev("Nonexistent Team") is None
