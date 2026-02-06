"""Tests for the transform layer."""

from src.transform.clean import normalize_player_name
from src.transform.normalize import normalize_position, normalize_team


class TestNormalizePlayerName:
    def test_strips_whitespace(self) -> None:
        assert normalize_player_name("  Connor McDavid  ") == "Connor McDavid"

    def test_removes_accents(self) -> None:
        assert normalize_player_name("Léon Draisaitl") == "Leon Draisaitl"

    def test_collapses_multiple_spaces(self) -> None:
        assert normalize_player_name("Nathan   MacKinnon") == "Nathan MacKinnon"

    def test_handles_already_clean(self) -> None:
        assert normalize_player_name("Cale Makar") == "Cale Makar"


class TestNormalizeTeam:
    def test_canonical_abbrev(self) -> None:
        assert normalize_team("COL") == "COL"

    def test_alternate_abbrev(self) -> None:
        assert normalize_team("MON") == "MTL"
        assert normalize_team("NAS") == "NSH"
        assert normalize_team("VEG") == "VGK"

    def test_relocated_team(self) -> None:
        assert normalize_team("ARI") == "UTA"

    def test_case_insensitive(self) -> None:
        assert normalize_team("col") == "COL"


class TestNormalizePosition:
    def test_wing_normalization(self) -> None:
        assert normalize_position("L") == "LW"
        assert normalize_position("R") == "RW"

    def test_center_stays(self) -> None:
        assert normalize_position("C") == "C"

    def test_goalie_stays(self) -> None:
        assert normalize_position("G") == "G"
