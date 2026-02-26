"""Tests for DailyFaceoff line combination parsing."""

import json

from src.extract.daily_faceoff import (
    ABBREV_TO_DF_SLUG,
    _build_player_line,
    _build_team_lines,
    _extract_next_data,
    _sort_players_by_position,
)

# Sample __NEXT_DATA__ payload for testing
SAMPLE_COMBINATIONS: list[dict[str, object]] = [
    # Forward Line 1
    {
        "playerId": 100,
        "name": "Artturi Lehkonen",
        "positionIdentifier": "lw",
        "positionName": "Left Wing",
        "groupIdentifier": "f1",
        "groupName": "Forwards 1",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    {
        "playerId": 101,
        "name": "Nathan MacKinnon",
        "positionIdentifier": "c",
        "positionName": "Center",
        "groupIdentifier": "f1",
        "groupName": "Forwards 1",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": True,
    },
    {
        "playerId": 102,
        "name": "Mikko Rantanen",
        "positionIdentifier": "rw",
        "positionName": "Right Wing",
        "groupIdentifier": "f1",
        "groupName": "Forwards 1",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    # Defense Pair 1
    {
        "playerId": 200,
        "name": "Devon Toews",
        "positionIdentifier": "ld",
        "positionName": "Left Defense",
        "groupIdentifier": "d1",
        "groupName": "Defense 1",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    {
        "playerId": 201,
        "name": "Cale Makar",
        "positionIdentifier": "rd",
        "positionName": "Right Defense",
        "groupIdentifier": "d1",
        "groupName": "Defense 1",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    # Power Play 1
    {
        "playerId": 100,
        "name": "Artturi Lehkonen",
        "positionIdentifier": "sk1",
        "positionName": "Skater",
        "groupIdentifier": "pp1",
        "groupName": "1st Powerplay Unit",
        "categoryIdentifier": "pp",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    {
        "playerId": 101,
        "name": "Nathan MacKinnon",
        "positionIdentifier": "sk2",
        "positionName": "Skater",
        "groupIdentifier": "pp1",
        "groupName": "1st Powerplay Unit",
        "categoryIdentifier": "pp",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    # Penalty Kill 1
    {
        "playerId": 300,
        "name": "Ross Colton",
        "positionIdentifier": "sk1",
        "positionName": "Skater",
        "groupIdentifier": "pk1",
        "groupName": "1st Penalty Kill Unit",
        "categoryIdentifier": "pk",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    # Goalies
    {
        "playerId": 400,
        "name": "Mackenzie Blackwood",
        "positionIdentifier": "g1",
        "positionName": "Starting Goalie",
        "groupIdentifier": "g",
        "groupName": "Goalies",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    {
        "playerId": 401,
        "name": "Scott Wedgewood",
        "positionIdentifier": "g2",
        "positionName": "Backup Goalie",
        "groupIdentifier": "g",
        "groupName": "Goalies",
        "categoryIdentifier": "ev",
        "injuryStatus": None,
        "gameTimeDecision": False,
    },
    # Injured player
    {
        "playerId": 500,
        "name": "Gabriel Landeskog",
        "positionIdentifier": "lw",
        "positionName": "Left Wing",
        "groupIdentifier": "ir",
        "groupName": "Injured Reserve",
        "categoryIdentifier": "oi",
        "injuryStatus": "out",
        "gameTimeDecision": False,
    },
    # DTD player on forward line 2
    {
        "playerId": 501,
        "name": "Valeri Nichushkin",
        "positionIdentifier": "rw",
        "positionName": "Right Wing",
        "groupIdentifier": "f2",
        "groupName": "Forwards 2",
        "categoryIdentifier": "ev",
        "injuryStatus": "dtd",
        "gameTimeDecision": False,
    },
]


class TestSlugMapping:
    """Verify team abbreviation to DailyFaceoff slug mapping."""

    def test_all_32_teams_mapped(self) -> None:
        """ABBREV_TO_DF_SLUG covers all 32 current NHL teams."""
        assert len(ABBREV_TO_DF_SLUG) == 32

    def test_known_slugs(self) -> None:
        """Spot-check a few known team slugs."""
        assert ABBREV_TO_DF_SLUG["COL"] == "colorado-avalanche"
        assert ABBREV_TO_DF_SLUG["EDM"] == "edmonton-oilers"
        assert ABBREV_TO_DF_SLUG["TOR"] == "toronto-maple-leafs"
        assert ABBREV_TO_DF_SLUG["MTL"] == "montreal-canadiens"
        assert ABBREV_TO_DF_SLUG["STL"] == "st-louis-blues"

    def test_utah_mammoth_slug(self) -> None:
        """Utah Mammoth uses the current franchise slug."""
        assert ABBREV_TO_DF_SLUG["UTA"] == "utah-mammoth"

    def test_all_slugs_are_lowercase_kebab(self) -> None:
        """All slugs follow lowercase-kebab-case convention."""
        for abbrev, slug in ABBREV_TO_DF_SLUG.items():
            assert slug == slug.lower(), f"{abbrev} slug not lowercase: {slug}"
            assert " " not in slug, f"{abbrev} slug has spaces: {slug}"


class TestExtractNextData:
    """Test __NEXT_DATA__ JSON extraction from HTML."""

    def test_extracts_valid_json(self) -> None:
        """Parses JSON from a __NEXT_DATA__ script tag."""
        payload = {"props": {"pageProps": {"combinations": []}}}
        html = (
            '<html><head><script id="__NEXT_DATA__" '
            'type="application/json">'
            f"{json.dumps(payload)}</script></head></html>"
        )
        result = _extract_next_data(html)
        assert result == payload

    def test_returns_none_for_missing_tag(self) -> None:
        """Returns None when no __NEXT_DATA__ tag exists."""
        html = "<html><body>No data here</body></html>"
        assert _extract_next_data(html) is None

    def test_returns_none_for_malformed_json(self) -> None:
        """Returns None when JSON is malformed."""
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            "{not valid json</script>"
        )
        assert _extract_next_data(html) is None

    def test_returns_none_for_unclosed_script(self) -> None:
        """Returns None when script tag is not closed."""
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            '{"data": true}'
        )
        assert _extract_next_data(html) is None


class TestBuildTeamLines:
    """Test conversion of raw combinations into TeamLines."""

    def test_forward_lines_parsed(self) -> None:
        """Forward line 1 is parsed with correct players."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert len(team.forward_lines) >= 1
        f1 = team.forward_lines[0]
        assert f1.group_id == "f1"
        assert f1.group_name == "Forwards 1"
        assert f1.group_type == "ev"
        assert len(f1.players) == 3
        names = [p.name for p in f1.players]
        assert "Nathan MacKinnon" in names

    def test_forward_line_position_order(self) -> None:
        """Forward line players are sorted LW → C → RW."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        f1 = team.forward_lines[0]
        positions = [p.position for p in f1.players]
        assert positions == ["LW", "C", "RW"]

    def test_defense_pairs_parsed(self) -> None:
        """Defense pair 1 is parsed with LD → RD ordering."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert len(team.defense_pairs) == 1
        d1 = team.defense_pairs[0]
        assert d1.group_id == "d1"
        assert len(d1.players) == 2
        assert d1.players[0].position == "LD"
        assert d1.players[1].position == "RD"

    def test_power_play_parsed(self) -> None:
        """Power play unit 1 is parsed."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert len(team.power_play) == 1
        pp1 = team.power_play[0]
        assert pp1.group_id == "pp1"
        assert pp1.group_type == "pp"

    def test_penalty_kill_parsed(self) -> None:
        """Penalty kill unit 1 is parsed."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert len(team.penalty_kill) == 1
        pk1 = team.penalty_kill[0]
        assert pk1.group_id == "pk1"
        assert pk1.group_type == "pk"

    def test_starting_goalie_identified(self) -> None:
        """Starting goalie (g1) is correctly identified."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert team.starting_goalie is not None
        assert team.starting_goalie.name == "Mackenzie Blackwood"
        assert team.starting_goalie.position == "G"

    def test_backup_goalie_identified(self) -> None:
        """Backup goalie (g2) is correctly identified."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        assert team.backup_goalie is not None
        assert team.backup_goalie.name == "Scott Wedgewood"

    def test_ir_players_excluded_from_lines(self) -> None:
        """IR players don't appear in forward/defense/special teams lines."""
        team = _build_team_lines(SAMPLE_COMBINATIONS, "COL")
        all_line_players = []
        for combo in (
            team.forward_lines + team.defense_pairs
            + team.power_play + team.penalty_kill
        ):
            all_line_players.extend(p.name for p in combo.players)
        assert "Gabriel Landeskog" not in all_line_players

    def test_empty_combinations(self) -> None:
        """Empty combinations list produces empty TeamLines."""
        team = _build_team_lines([], "COL")
        assert team.team_abbrev == "COL"
        assert team.forward_lines == []
        assert team.defense_pairs == []
        assert team.starting_goalie is None


class TestBuildPlayerLine:
    """Test individual player parsing."""

    def test_healthy_player(self) -> None:
        """Healthy player has no injury markers."""
        player = _build_player_line({
            "name": "Nathan MacKinnon",
            "positionIdentifier": "c",
            "injuryStatus": None,
            "gameTimeDecision": False,
        })
        assert player.name == "Nathan MacKinnon"
        assert player.position == "C"
        assert player.injury_status is None
        assert player.game_time_decision is False

    def test_injured_player(self) -> None:
        """Player with injuryStatus='out' is marked correctly."""
        player = _build_player_line({
            "name": "Gabriel Landeskog",
            "positionIdentifier": "lw",
            "injuryStatus": "out",
            "gameTimeDecision": False,
        })
        assert player.injury_status == "out"

    def test_dtd_player(self) -> None:
        """Player with injuryStatus='dtd' is marked correctly."""
        player = _build_player_line({
            "name": "Someone Hurt",
            "positionIdentifier": "rw",
            "injuryStatus": "dtd",
            "gameTimeDecision": False,
        })
        assert player.injury_status == "dtd"

    def test_game_time_decision(self) -> None:
        """Player with gameTimeDecision=True is flagged."""
        player = _build_player_line({
            "name": "Nathan MacKinnon",
            "positionIdentifier": "c",
            "injuryStatus": None,
            "gameTimeDecision": True,
        })
        assert player.game_time_decision is True

    def test_goalie_position_display(self) -> None:
        """Both g1 and g2 display as 'G'."""
        starter = _build_player_line({
            "name": "Starter",
            "positionIdentifier": "g1",
            "injuryStatus": None,
            "gameTimeDecision": False,
        })
        backup = _build_player_line({
            "name": "Backup",
            "positionIdentifier": "g2",
            "injuryStatus": None,
            "gameTimeDecision": False,
        })
        assert starter.position == "G"
        assert backup.position == "G"

    def test_special_teams_position_fallback(self) -> None:
        """PP/PK skater positions (sk1, sk2) fall back to uppercase."""
        player = _build_player_line({
            "name": "Someone",
            "positionIdentifier": "sk1",
            "injuryStatus": None,
            "gameTimeDecision": False,
        })
        assert player.position == "SK1"


class TestSortPlayersByPosition:
    """Test position-based sorting within line groups."""

    def test_forward_line_sorting(self) -> None:
        """Forward line players sort LW → C → RW regardless of input order."""
        players = [
            {"positionIdentifier": "rw", "name": "RW"},
            {"positionIdentifier": "c", "name": "C"},
            {"positionIdentifier": "lw", "name": "LW"},
        ]
        sorted_p = _sort_players_by_position(players, "f1")
        positions = [str(p["positionIdentifier"]) for p in sorted_p]
        assert positions == ["lw", "c", "rw"]

    def test_defense_pair_sorting(self) -> None:
        """Defense pair sorts LD → RD."""
        players = [
            {"positionIdentifier": "rd", "name": "RD"},
            {"positionIdentifier": "ld", "name": "LD"},
        ]
        sorted_p = _sort_players_by_position(players, "d1")
        positions = [str(p["positionIdentifier"]) for p in sorted_p]
        assert positions == ["ld", "rd"]

    def test_pp_preserves_order(self) -> None:
        """Power play players preserve original order."""
        players = [
            {"positionIdentifier": "sk3", "name": "Third"},
            {"positionIdentifier": "sk1", "name": "First"},
            {"positionIdentifier": "sk2", "name": "Second"},
        ]
        sorted_p = _sort_players_by_position(players, "pp1")
        names = [str(p["name"]) for p in sorted_p]
        assert names == ["Third", "First", "Second"]
