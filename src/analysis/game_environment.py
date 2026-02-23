"""Game environment classification for DFS slate analysis.

This is the core analytical framework: classify each game on tonight's slate
into chalk / leverage / contrarian / avoid tiers based on Vegas lines and
underlying shot quality metrics.

The idea: most DFS players pick players. This framework picks GAMES first,
then finds players within the right game environments. Game selection > player selection.

Classification logic:
    CHALK — High total (6.0+), strong shot quality on both sides (both HDCF% near 50%+).
            Everyone will be here. You need some exposure (25% of entries) but the
            ownership will be high so ceiling is capped.

    LEVERAGE — Moderate-to-high total (5.5+), but one team has a clear shot quality
               advantage that the market may be underpricing. This is where edges live.
               50% of entries.

    CONTRARIAN — Low total (<5.5) OR games where Vegas total disagrees with underlying
                 shot quality (divergence). Thin ownership = GPP upside if it hits.
                 25% of entries.

    AVOID — Games with no clear edge or poor data.

Divergence detection:
    Flag games where the Vegas implied total and shot quality metrics disagree.
    Example: PHI has a 4.07 implied total but only 72.8 HDSF+ — the market
    is pricing in offense the shot quality doesn't support. That's a trap.
"""

from src.models.slate import (
    GameEnvironment,
    GameOdds,
    GameSlateEntry,
    SlateBreakdown,
    TeamShotQuality,
)

# Thresholds for classification — these encode the framework
HIGH_TOTAL_THRESHOLD = 6.0
MODERATE_TOTAL_THRESHOLD = 5.5

# HDCF% thresholds (50% = league average at 5v5)
STRONG_HDCF_PCT = 52.0    # Meaningfully above average
WEAK_HDCF_PCT = 47.0      # Meaningfully below average

# xGF% thresholds
STRONG_XGF_PCT = 52.0
WEAK_XGF_PCT = 47.0

# PDO thresholds — PDO (sh% + sv%) regresses to ~100.
# High PDO = running hot (luck), low PDO = running cold.
HIGH_PDO = 101.5
LOW_PDO = 98.5

# Divergence: implied total vs shot quality mismatch
DIVERGENCE_TOTAL_THRESHOLD = 3.0   # Implied team total this high...
DIVERGENCE_HDCF_THRESHOLD = 47.0   # ...but HDCF% this low = divergence


def classify_game(
    odds: GameOdds,
    home_quality: TeamShotQuality | None,
    away_quality: TeamShotQuality | None,
) -> GameSlateEntry:
    """Classify a single game's environment from odds + shot quality.

    Args:
        odds: Vegas odds for the game.
        home_quality: Home team's shot quality metrics (None if unavailable).
        away_quality: Away team's shot quality metrics (None if unavailable).

    Returns:
        GameSlateEntry with environment classification and supporting data.
    """
    entry = GameSlateEntry(
        home_team=odds.home_team,
        away_team=odds.away_team,
        commence_time=odds.commence_time,
        total=odds.total,
        home_implied_total=odds.home_implied_total,
        away_implied_total=odds.away_implied_total,
        home_ml=odds.home_ml,
        away_ml=odds.away_ml,
        home_spread=odds.home_spread,
    )

    # Attach shot quality data if available
    if home_quality:
        entry.home_hdcf_pct = home_quality.hdcf_pct
        entry.home_xgf_pct = home_quality.xgf_pct
        entry.home_hdcf_per_60 = home_quality.hdcf_per_60
        entry.home_hdca_per_60 = home_quality.hdca_per_60
        entry.home_pdo = home_quality.pdo

    if away_quality:
        entry.away_hdcf_pct = away_quality.hdcf_pct
        entry.away_xgf_pct = away_quality.xgf_pct
        entry.away_hdcf_per_60 = away_quality.hdcf_per_60
        entry.away_hdca_per_60 = away_quality.hdca_per_60
        entry.away_pdo = away_quality.pdo

    # Check for divergence first — this is the most actionable signal
    _check_divergence(entry, home_quality, away_quality)

    # Classify environment
    _classify_environment(entry, home_quality, away_quality)

    return entry


def _check_divergence(
    entry: GameSlateEntry,
    home_quality: TeamShotQuality | None,
    away_quality: TeamShotQuality | None,
) -> None:
    """Flag games where Vegas totals and shot quality disagree."""
    flags: list[str] = []

    # Home team: high implied total but poor shot quality
    if home_quality and home_quality.hdcf_pct is not None:
        if (
            entry.home_implied_total >= DIVERGENCE_TOTAL_THRESHOLD
            and home_quality.hdcf_pct < DIVERGENCE_HDCF_THRESHOLD
        ):
            flags.append(
                f"{entry.home_team}: {entry.home_implied_total:.1f} implied total "
                f"but only {home_quality.hdcf_pct:.1f}% HDCF — market overpricing offense"
            )

    # Away team: same check
    if away_quality and away_quality.hdcf_pct is not None:
        if (
            entry.away_implied_total >= DIVERGENCE_TOTAL_THRESHOLD
            and away_quality.hdcf_pct < DIVERGENCE_HDCF_THRESHOLD
        ):
            flags.append(
                f"{entry.away_team}: {entry.away_implied_total:.1f} implied total "
                f"but only {away_quality.hdcf_pct:.1f}% HDCF — market overpricing offense"
            )

    # High PDO = running hot, likely to regress
    if home_quality and home_quality.pdo is not None and home_quality.pdo > HIGH_PDO:
        flags.append(
            f"{entry.home_team}: PDO at {home_quality.pdo:.1f} — running hot, regression risk"
        )
    if away_quality and away_quality.pdo is not None and away_quality.pdo > HIGH_PDO:
        flags.append(
            f"{entry.away_team}: PDO at {away_quality.pdo:.1f} — running hot, regression risk"
        )

    if flags:
        entry.divergence_flag = True
        entry.divergence_detail = "; ".join(flags)


def _classify_environment(
    entry: GameSlateEntry,
    home_quality: TeamShotQuality | None,
    away_quality: TeamShotQuality | None,
) -> None:
    """Assign chalk / leverage / contrarian / avoid tier."""
    total = entry.total
    has_quality_data = home_quality is not None and away_quality is not None

    # Without shot quality data, classify purely on total
    if not has_quality_data:
        if total >= HIGH_TOTAL_THRESHOLD:
            entry.environment = GameEnvironment.CHALK
            entry.environment_reason = (
                f"High total ({total}) — no shot quality data to differentiate further"
            )
        elif total >= MODERATE_TOTAL_THRESHOLD:
            entry.environment = GameEnvironment.LEVERAGE
            entry.environment_reason = (
                f"Moderate total ({total}) — no shot quality data available"
            )
        else:
            entry.environment = GameEnvironment.CONTRARIAN
            entry.environment_reason = f"Low total ({total})"
        return

    assert home_quality is not None  # narrowed by has_quality_data check above
    assert away_quality is not None
    home_hdcf = home_quality.hdcf_pct if home_quality.hdcf_pct is not None else 50.0
    away_hdcf = away_quality.hdcf_pct if away_quality.hdcf_pct is not None else 50.0

    home_strong = home_hdcf >= STRONG_HDCF_PCT
    away_strong = away_hdcf >= STRONG_HDCF_PCT
    home_weak = home_hdcf < WEAK_HDCF_PCT
    away_weak = away_hdcf < WEAK_HDCF_PCT

    # CHALK: High total + both teams generating quality chances
    if total >= HIGH_TOTAL_THRESHOLD and home_strong and away_strong:
        entry.environment = GameEnvironment.CHALK
        entry.environment_reason = (
            f"High total ({total}) with strong shot quality on both sides "
            f"(home HDCF% {home_hdcf:.1f}, away HDCF% {away_hdcf:.1f}). "
            f"Expect high ownership — core game for the slate."
        )
        return

    # LEVERAGE: Good total + one side has a clear quality edge
    if total >= MODERATE_TOTAL_THRESHOLD:
        if home_strong and away_weak:
            entry.environment = GameEnvironment.LEVERAGE
            entry.environment_reason = (
                f"Total {total} with {entry.home_team} dominating shot quality "
                f"(HDCF% {home_hdcf:.1f} vs {away_hdcf:.1f}). "
                f"Home stacks are the play — the quality edge is real."
            )
            return
        if away_strong and home_weak:
            entry.environment = GameEnvironment.LEVERAGE
            entry.environment_reason = (
                f"Total {total} with {entry.away_team} dominating shot quality "
                f"(HDCF% {away_hdcf:.1f} vs {home_hdcf:.1f}). "
                f"Away stacks are the play — the quality edge is real."
            )
            return
        # Both moderate — still leverage if total is decent
        if total >= HIGH_TOTAL_THRESHOLD:
            entry.environment = GameEnvironment.CHALK
            entry.environment_reason = (
                f"High total ({total}) with moderate shot quality on both sides "
                f"(home HDCF% {home_hdcf:.1f}, away HDCF% {away_hdcf:.1f})."
            )
            return
        entry.environment = GameEnvironment.LEVERAGE
        entry.environment_reason = (
            f"Moderate total ({total}) with balanced shot quality "
            f"(home HDCF% {home_hdcf:.1f}, away HDCF% {away_hdcf:.1f})."
        )
        return

    # CONTRARIAN: Low total OR divergence trap
    if entry.divergence_flag:
        entry.environment = GameEnvironment.CONTRARIAN
        entry.environment_reason = (
            f"Divergence detected — Vegas total ({total}) disagrees with shot quality. "
            f"Low ownership expected. GPP-only play."
        )
        return

    # Low total games
    if total < MODERATE_TOTAL_THRESHOLD:
        # But if one team has strong shot quality, there could be sneaky upside
        if home_strong or away_strong:
            entry.environment = GameEnvironment.CONTRARIAN
            entry.environment_reason = (
                f"Low total ({total}) but "
                f"{'home' if home_strong else 'away'} team "
                f"has strong shot quality. Low ownership = GPP upside."
            )
        else:
            entry.environment = GameEnvironment.AVOID
            entry.environment_reason = (
                f"Low total ({total}) with weak shot quality on both sides "
                f"(home HDCF% {home_hdcf:.1f}, away HDCF% {away_hdcf:.1f}). No edge."
            )
        return

    # Fallback
    entry.environment = GameEnvironment.AVOID
    entry.environment_reason = "No clear classification — insufficient signal."


def build_slate_breakdown(
    odds_list: list[GameOdds],
    shot_quality: dict[str, TeamShotQuality],
) -> SlateBreakdown:
    """Build a full slate breakdown from odds + shot quality data.

    Args:
        odds_list: List of GameOdds for tonight's games.
        shot_quality: Dict of team abbrev → TeamShotQuality.

    Returns:
        SlateBreakdown with all games classified.
    """
    games = []
    for odds in odds_list:
        home_q = _find_team_quality(odds.home_team, shot_quality)
        away_q = _find_team_quality(odds.away_team, shot_quality)
        entry = classify_game(odds, home_q, away_q)
        games.append(entry)

    # Sort: chalk first, then leverage, then contrarian, then avoid
    tier_order = {
        GameEnvironment.CHALK: 0,
        GameEnvironment.LEVERAGE: 1,
        GameEnvironment.CONTRARIAN: 2,
        GameEnvironment.AVOID: 3,
    }
    games.sort(key=lambda g: (tier_order.get(g.environment, 99), -g.total))

    return SlateBreakdown(games=games)


def _find_team_quality(
    team_name: str,
    shot_quality: dict[str, TeamShotQuality],
) -> TeamShotQuality | None:
    """Look up a team's shot quality by full name or abbreviation.

    The Odds API uses full team names (e.g., 'Carolina Hurricanes')
    while Natural Stat Trick uses abbreviations (e.g., 'CAR').
    Try both.
    """
    # Direct match (by abbrev or full name)
    if team_name in shot_quality:
        return shot_quality[team_name]

    # Try matching by checking if any key is a substring of the team name
    # or vice versa (handles "Carolina Hurricanes" matching "CAR")
    for key, quality in shot_quality.items():
        if key in team_name or team_name in key:
            return quality

    return None
