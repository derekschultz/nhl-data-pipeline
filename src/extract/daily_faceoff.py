"""Scraper for DailyFaceoff.com line combinations and goalie confirmations.

DailyFaceoff publishes projected line combinations for all 32 NHL teams,
including forward lines, defense pairs, power play/penalty kill units,
starting/backup goalies, and injury statuses. The data is embedded as
structured JSON in their Next.js pages (__NEXT_DATA__ script tag).

URL pattern:
    https://www.dailyfaceoff.com/teams/{slug}/line-combinations/
    e.g., colorado-avalanche, edmonton-oilers

Data available per team:
    - Forward lines 1-4 (LW-C-RW)
    - Defense pairs 1-3 (LD-RD)
    - PP1/PP2 units
    - PK1/PK2 units
    - Starting/backup goalie
    - Injury status (out/dtd/game-time decision)
"""

import json
import logging
import time

import httpx

from src.models.slate import LineCombination, PlayerLine, TeamLines

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dailyfaceoff.com/teams"

# Map NHL team abbreviations to DailyFaceoff URL slugs
ABBREV_TO_DF_SLUG: dict[str, str] = {
    "ANA": "anaheim-ducks",
    "BOS": "boston-bruins",
    "BUF": "buffalo-sabres",
    "CAR": "carolina-hurricanes",
    "CBJ": "columbus-blue-jackets",
    "CGY": "calgary-flames",
    "CHI": "chicago-blackhawks",
    "COL": "colorado-avalanche",
    "DAL": "dallas-stars",
    "DET": "detroit-red-wings",
    "EDM": "edmonton-oilers",
    "FLA": "florida-panthers",
    "LAK": "los-angeles-kings",
    "MIN": "minnesota-wild",
    "MTL": "montreal-canadiens",
    "NJD": "new-jersey-devils",
    "NSH": "nashville-predators",
    "NYI": "new-york-islanders",
    "NYR": "new-york-rangers",
    "OTT": "ottawa-senators",
    "PHI": "philadelphia-flyers",
    "PIT": "pittsburgh-penguins",
    "SEA": "seattle-kraken",
    "SJS": "san-jose-sharks",
    "STL": "st-louis-blues",
    "TBL": "tampa-bay-lightning",
    "TOR": "toronto-maple-leafs",
    "UTA": "utah-mammoth",
    "VAN": "vancouver-canucks",
    "VGK": "vegas-golden-knights",
    "WPG": "winnipeg-jets",
    "WSH": "washington-capitals",
}

# Ordered position identifiers for consistent display
_FORWARD_POSITIONS = ("lw", "c", "rw")
_DEFENSE_POSITIONS = ("ld", "rd")

# Map DailyFaceoff position identifiers to display abbreviations
_POSITION_DISPLAY: dict[str, str] = {
    "lw": "LW",
    "c": "C",
    "rw": "RW",
    "ld": "LD",
    "rd": "RD",
    "g1": "G",
    "g2": "G",
}


def fetch_team_lines(team_abbrev: str) -> TeamLines | None:
    """Fetch line combinations for a single team from DailyFaceoff.

    Args:
        team_abbrev: NHL team abbreviation (e.g., "COL").

    Returns:
        TeamLines with parsed line data, or None if fetch/parse fails.
    """
    slug = ABBREV_TO_DF_SLUG.get(team_abbrev)
    if not slug:
        logger.warning("No DailyFaceoff slug for team: %s", team_abbrev)
        return None

    url = f"{BASE_URL}/{slug}/line-combinations/"
    logger.info("Fetching line combinations for %s from %s", team_abbrev, url)

    try:
        response = httpx.get(
            url,
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; NHLDataPipeline/1.0; "
                    "personal research tool)"
                ),
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch DailyFaceoff page for %s: %s", team_abbrev, e)
        return None

    return _parse_lines_from_html(response.text, team_abbrev)


def fetch_lines_for_teams(team_abbrevs: list[str]) -> dict[str, TeamLines]:
    """Fetch line combinations for multiple teams with polite rate limiting.

    Args:
        team_abbrevs: List of NHL team abbreviations.

    Returns:
        Dict of team abbreviation → TeamLines (only teams that succeeded).
    """
    results: dict[str, TeamLines] = {}

    for i, abbrev in enumerate(team_abbrevs):
        lines = fetch_team_lines(abbrev)
        if lines is not None:
            results[abbrev] = lines

        # Polite delay between requests (skip after last)
        if i < len(team_abbrevs) - 1:
            time.sleep(1.5)

    logger.info(
        "Fetched line combinations for %d/%d teams",
        len(results),
        len(team_abbrevs),
    )
    return results


def _parse_lines_from_html(html: str, team_abbrev: str) -> TeamLines | None:
    """Extract line combination data from DailyFaceoff HTML page.

    Parses the __NEXT_DATA__ JSON embedded in the page's script tag.
    The combinations object contains a `players` list with all player entries.
    """
    next_data = _extract_next_data(html)
    if next_data is None:
        logger.warning("No __NEXT_DATA__ found for %s", team_abbrev)
        return None

    try:
        combinations = next_data["props"]["pageProps"]["combinations"]
        players = combinations["players"]
    except (KeyError, TypeError):
        logger.warning("Unexpected __NEXT_DATA__ structure for %s", team_abbrev)
        return None

    if not isinstance(players, list):
        logger.warning("Expected players list, got %s for %s", type(players), team_abbrev)
        return None

    return _build_team_lines(players, team_abbrev)


def _extract_next_data(html: str) -> dict | None:  # type: ignore[type-arg]
    """Extract and parse the __NEXT_DATA__ JSON from HTML."""
    marker = '<script id="__NEXT_DATA__" type="application/json">'
    start = html.find(marker)
    if start == -1:
        return None

    start += len(marker)
    end = html.find("</script>", start)
    if end == -1:
        return None

    try:
        return json.loads(html[start:end])  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        logger.warning("Failed to parse __NEXT_DATA__ JSON")
        return None


def _build_team_lines(
    combinations: list[dict[str, object]],
    team_abbrev: str,
) -> TeamLines:
    """Build TeamLines from the parsed combinations array."""
    team = TeamLines(team_abbrev=team_abbrev)

    # Group players by their group_id (f1, d1, pp1, etc.)
    groups: dict[str, list[dict[str, object]]] = {}
    for player in combinations:
        gid = str(player.get("groupIdentifier", ""))
        if gid:
            groups.setdefault(gid, []).append(player)

    # Forward lines (f1-f4)
    for i in range(1, 5):
        gid = f"f{i}"
        if gid in groups:
            combo = _build_line_combination(groups[gid], gid)
            if combo:
                team.forward_lines.append(combo)

    # Defense pairs (d1-d3)
    for i in range(1, 4):
        gid = f"d{i}"
        if gid in groups:
            combo = _build_line_combination(groups[gid], gid)
            if combo:
                team.defense_pairs.append(combo)

    # Power play (pp1-pp2)
    for i in range(1, 3):
        gid = f"pp{i}"
        if gid in groups:
            combo = _build_line_combination(groups[gid], gid)
            if combo:
                team.power_play.append(combo)

    # Penalty kill (pk1-pk2)
    for i in range(1, 3):
        gid = f"pk{i}"
        if gid in groups:
            combo = _build_line_combination(groups[gid], gid)
            if combo:
                team.penalty_kill.append(combo)

    # Goalies
    if "g" in groups:
        for player in groups["g"]:
            pos_id = str(player.get("positionIdentifier", ""))
            pl = _build_player_line(player)
            if pos_id == "g1":
                team.starting_goalie = pl
            elif pos_id == "g2":
                team.backup_goalie = pl

    return team


def _build_line_combination(
    players: list[dict[str, object]],
    group_id: str,
) -> LineCombination | None:
    """Build a LineCombination from a group of player dicts."""
    if not players:
        return None

    first = players[0]
    group_type = str(first.get("categoryIdentifier", "ev"))
    group_name = str(first.get("groupName", ""))

    # Sort players by position for consistent ordering
    sorted_players = _sort_players_by_position(players, group_id)

    return LineCombination(
        group_type=group_type,
        group_name=group_name,
        group_id=group_id,
        players=[_build_player_line(p) for p in sorted_players],
    )


def _build_player_line(player: dict[str, object]) -> PlayerLine:
    """Build a PlayerLine from a single player dict."""
    pos_id = str(player.get("positionIdentifier", ""))
    position = _POSITION_DISPLAY.get(pos_id, pos_id.upper())

    injury_raw = player.get("injuryStatus")
    injury_status = str(injury_raw) if injury_raw else None

    gtd = player.get("gameTimeDecision")
    game_time_decision = bool(gtd) if gtd is not None else False

    return PlayerLine(
        name=str(player.get("name", "")),
        position=position,
        injury_status=injury_status,
        game_time_decision=game_time_decision,
    )


def _sort_players_by_position(
    players: list[dict[str, object]],
    group_id: str,
) -> list[dict[str, object]]:
    """Sort players within a group by position for consistent display.

    Forward lines: LW → C → RW
    Defense pairs: LD → RD
    Special teams (PP/PK): preserve original order (mixed positions)
    """
    if group_id.startswith("f"):
        order = {pos: i for i, pos in enumerate(_FORWARD_POSITIONS)}
        return sorted(
            players,
            key=lambda p: order.get(str(p.get("positionIdentifier", "")), 99),
        )

    if group_id.startswith("d"):
        order = {pos: i for i, pos in enumerate(_DEFENSE_POSITIONS)}
        return sorted(
            players,
            key=lambda p: order.get(str(p.get("positionIdentifier", "")), 99),
        )

    # PP/PK: keep original order
    return players
