"""Parse NHL API JSON responses into dataclass instances."""

import logging
from datetime import date, datetime

from src.models.game import Game
from src.models.player import Player
from src.models.stats import GoalieGameStats, SkaterGameStats

logger = logging.getLogger(__name__)


def parse_games(scores_response: dict) -> list[Game]:
    """Parse /score/{date} response into Game dataclasses.

    Args:
        scores_response: Raw JSON from the NHL scores endpoint.

    Returns:
        List of Game dataclass instances.
    """
    games: list[Game] = []
    for g in scores_response.get("games", []):
        start_time = None
        if g.get("startTimeUTC"):
            try:
                start_time = datetime.fromisoformat(g["startTimeUTC"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        game = Game(
            game_id=g["id"],
            season=str(g.get("season", "")),
            game_type=g.get("gameType", 2),
            game_date=date.fromisoformat(g["gameDate"]),
            home_team_abbrev=g["homeTeam"]["abbrev"],
            away_team_abbrev=g["awayTeam"]["abbrev"],
            home_score=g.get("homeTeam", {}).get("score"),
            away_score=g.get("awayTeam", {}).get("score"),
            venue=g.get("venue", {}).get("default") if g.get("venue") else None,
            start_time_utc=start_time,
            game_state=g.get("gameState"),
        )
        games.append(game)

    logger.info("Parsed %d games from scores response", len(games))
    return games


def parse_skater_stats(boxscore: dict, game_id: int) -> list[SkaterGameStats]:
    """Parse boxscore playerByGameStats into SkaterGameStats.

    Extracts forwards and defense from both home and away teams.

    Args:
        boxscore: Raw JSON from the NHL boxscore endpoint.
        game_id: The game ID to associate stats with.

    Returns:
        List of SkaterGameStats dataclass instances.
    """
    stats: list[SkaterGameStats] = []

    for side in ("homeTeam", "awayTeam"):
        team_data = boxscore.get("playerByGameStats", {}).get(side, {})
        team_abbrev = boxscore.get(side, {}).get("abbrev", "")

        for position_group in ("forwards", "defense"):
            for player in team_data.get(position_group, []):
                stat = SkaterGameStats(
                    player_id=player["playerId"],
                    game_id=game_id,
                    team_abbrev=team_abbrev,
                    goals=player.get("goals", 0),
                    assists=player.get("assists", 0),
                    points=player.get("points", 0),
                    shots=player.get("sog", 0),
                    hits=player.get("hits", 0),
                    blocked_shots=player.get("blockedShots", 0),
                    pim=player.get("pim", 0),
                    toi_seconds=_toi_str_to_seconds(player.get("toi", "0:00")),
                    plus_minus=player.get("plusMinus", 0),
                    power_play_goals=player.get("powerPlayGoals", 0),
                    power_play_points=player.get("powerPlayPoints", 0),
                    shorthanded_goals=player.get("shorthandedGoals", 0),
                    faceoff_pct=_parse_faceoff_pct(player.get("faceoffWinningPctg")),
                )
                stats.append(stat)

    logger.info("Parsed %d skater stat lines for game %d", len(stats), game_id)
    return stats


def parse_goalie_stats(boxscore: dict, game_id: int) -> list[GoalieGameStats]:
    """Parse boxscore playerByGameStats into GoalieGameStats.

    Args:
        boxscore: Raw JSON from the NHL boxscore endpoint.
        game_id: The game ID to associate stats with.

    Returns:
        List of GoalieGameStats dataclass instances.
    """
    stats: list[GoalieGameStats] = []

    for side in ("homeTeam", "awayTeam"):
        team_data = boxscore.get("playerByGameStats", {}).get(side, {})
        team_abbrev = boxscore.get(side, {}).get("abbrev", "")

        for player in team_data.get("goalies", []):
            stat = GoalieGameStats(
                player_id=player["playerId"],
                game_id=game_id,
                team_abbrev=team_abbrev,
                decision=player.get("decision"),
                shots_against=player.get("shotsAgainst", 0),
                saves=player.get("saves", 0),
                goals_against=player.get("goalsAgainst", 0),
                toi_seconds=_toi_str_to_seconds(player.get("toi", "0:00")),
                power_play_saves=player.get("powerPlaySaves", 0),
                shorthanded_saves=player.get("shorthandedSaves", 0),
                even_strength_saves=player.get("evenStrengthSaves", 0),
            )
            stats.append(stat)

    logger.info("Parsed %d goalie stat lines for game %d", len(stats), game_id)
    return stats


def parse_players(boxscore: dict) -> list[Player]:
    """Extract player info from boxscore for dim_player upserts.

    Args:
        boxscore: Raw JSON from the NHL boxscore endpoint.

    Returns:
        List of Player dataclass instances.
    """
    players: list[Player] = []
    seen_ids: set[int] = set()

    for side in ("homeTeam", "awayTeam"):
        team_data = boxscore.get("playerByGameStats", {}).get(side, {})
        team_abbrev = boxscore.get(side, {}).get("abbrev", "")

        for position_group in ("forwards", "defense", "goalies"):
            for p in team_data.get(position_group, []):
                pid = p["playerId"]
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                raw_name = p.get("name", {})
                if isinstance(raw_name, dict):
                    full = raw_name.get("default", "")
                else:
                    full = str(raw_name)
                parts = full.split(" ", 1)
                first = parts[0]
                last = parts[-1] if len(parts) > 1 else first

                player = Player(
                    player_id=pid,
                    first_name=first,
                    last_name=last,
                    position=p.get("position", ""),
                    team_abbrev=team_abbrev,
                    jersey_number=p.get("sweaterNumber"),
                )
                players.append(player)

    logger.info("Parsed %d players from boxscore", len(players))
    return players


def _toi_str_to_seconds(toi: str) -> int:
    """Convert TOI string 'MM:SS' to total seconds."""
    try:
        parts = toi.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 0


def _parse_faceoff_pct(value: object) -> float | None:
    """Parse faceoff percentage, handling various API formats."""
    if value is None:
        return None
    try:
        pct = float(value)  # type: ignore[arg-type]
        return pct if pct > 0 else None
    except (ValueError, TypeError):
        return None
