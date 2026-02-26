"""DFS Slate Breakdown dashboard page.

This is the core product: a pre-game slate research view that classifies
tonight's games into chalk / leverage / contrarian tiers using Vegas lines
and underlying shot quality data from public sources.

No projections. No optimizer. Just the game environment framework
that tells you WHICH GAMES to target and WHY.
"""

import logging
import os

import streamlit as st

from src.models.slate import (
    GameEnvironment,
    GameSlateEntry,
    LineCombination,
    PlayerLine,
    SlateBreakdown,
    TeamLines,
)

logger = logging.getLogger(__name__)

# Colors for environment tiers
ENV_COLORS = {
    GameEnvironment.CHALK: "#2196F3",       # Blue
    GameEnvironment.LEVERAGE: "#4CAF50",     # Green
    GameEnvironment.CONTRARIAN: "#FF9800",   # Orange
    GameEnvironment.AVOID: "#9E9E9E",        # Gray
}

ENV_ICONS = {
    GameEnvironment.CHALK: "CHALK",
    GameEnvironment.LEVERAGE: "LEVERAGE",
    GameEnvironment.CONTRARIAN: "CONTRARIAN",
    GameEnvironment.AVOID: "AVOID",
}

ALLOCATION_GUIDE = {
    GameEnvironment.CHALK: "~25% of entries",
    GameEnvironment.LEVERAGE: "~50% of entries",
    GameEnvironment.CONTRARIAN: "~25% of entries (GPP only)",
    GameEnvironment.AVOID: "Minimal or no exposure",
}


def render_slate_breakdown() -> None:
    """Main entry point for the slate breakdown page."""
    st.header("DFS Slate Breakdown")
    st.markdown(
        "*Game environment first, players second. "
        "Pick the right games, then build correlated stacks within them.*"
    )

    # Allow manual cache refresh
    if st.button("Refresh slate data"):
        _cached_build_slate.clear()

    api_key = os.environ.get("ODDS_API_KEY", "")

    if not api_key:
        st.warning(
            "**ODDS_API_KEY not set.** Set it in your `.env` file to fetch live odds.\n\n"
            "Get a free key (500 credits/month) at https://the-odds-api.com\n\n"
            "Showing demo mode with sample data."
        )
        slate: SlateBreakdown | None = _demo_slate()
    else:
        slate = _fetch_live_slate(api_key)

    if slate is None or not slate.games:
        st.info("No games on tonight's slate. Check back on game day.")
        return

    _render_allocation_summary(slate)
    st.divider()
    _render_divergence_alerts(slate)
    _render_game_tiers(slate)


def _fetch_live_slate(api_key: str) -> SlateBreakdown | None:
    """Fetch live slate data with a loading spinner."""
    try:
        with st.spinner("Fetching odds, shot quality, and line combinations..."):
            return _cached_build_slate(api_key)
    except Exception as e:
        st.error(f"Failed to fetch slate data: {e}")
        logger.exception("Slate fetch failed")
        return None


@st.cache_data(ttl=900, show_spinner=False)
def _cached_build_slate(api_key: str) -> SlateBreakdown:
    """Build tonight's slate. Cached for 15 minutes."""
    from src.analysis.slate_builder import build_tonight_slate
    return build_tonight_slate(odds_api_key=api_key)


def _render_allocation_summary(slate: SlateBreakdown) -> None:
    """Render the top-level allocation summary."""
    st.subheader("Entry Allocation Guide")

    cols = st.columns(4)

    tier_data = [
        (GameEnvironment.CHALK, slate.chalk_games, "25%"),
        (GameEnvironment.LEVERAGE, slate.leverage_games, "50%"),
        (GameEnvironment.CONTRARIAN, slate.contrarian_games, "25%"),
        (GameEnvironment.AVOID, slate.avoid_games, "0%"),
    ]

    for col, (env, games, target) in zip(cols, tier_data):
        color = ENV_COLORS[env]
        col.markdown(
            f'<div style="border-left: 4px solid {color}; padding-left: 12px;">'
            f"<strong>{env.value.upper()}</strong><br>"
            f"{len(games)} game{'s' if len(games) != 1 else ''}<br>"
            f"<small>Target: {target} of entries</small>"
            f"</div>",
            unsafe_allow_html=True,
        )

    total_games = len(slate.games)
    st.caption(
        f"{total_games} total game{'s' if total_games != 1 else ''} on tonight's slate"
    )


def _render_divergence_alerts(slate: SlateBreakdown) -> None:
    """Render divergence alerts if any games have flags."""
    divergence_games = slate.divergence_games
    if not divergence_games:
        return

    st.subheader("Divergence Alerts")
    st.markdown(
        "*Games where Vegas totals disagree with underlying shot quality — "
        "potential traps or hidden value.*"
    )

    for game in divergence_games:
        st.warning(
            f"**{game.matchup}** (Total: {game.total})\n\n"
            f"{game.divergence_detail}"
        )


def _render_game_tiers(slate: SlateBreakdown) -> None:
    """Render games grouped by environment tier."""

    # Chalk games
    if slate.chalk_games:
        _render_tier_section(
            "Chalk Games",
            slate.chalk_games,
            GameEnvironment.CHALK,
            "High total + strong shot quality on both sides. "
            "Everyone will be here — you need exposure but don't overweight. "
            "Build 25% of entries around these stacks.",
        )

    # Leverage games
    if slate.leverage_games:
        _render_tier_section(
            "Leverage Games",
            slate.leverage_games,
            GameEnvironment.LEVERAGE,
            "This is where edges live. One team has a shot quality advantage "
            "the market may be underpricing. Build 50% of entries here — "
            "correlated stacks on the right side of the matchup.",
        )

    # Contrarian games
    if slate.contrarian_games:
        _render_tier_section(
            "Contrarian Games",
            slate.contrarian_games,
            GameEnvironment.CONTRARIAN,
            "Low totals, divergences, or trap games. Thin ownership = GPP upside "
            "if it hits. 25% of entries max — these are lottery tickets.",
        )

    # Avoid games
    if slate.avoid_games:
        _render_tier_section(
            "Avoid",
            slate.avoid_games,
            GameEnvironment.AVOID,
            "No clear edge. Minimal or no exposure.",
        )


def _render_tier_section(
    title: str,
    games: list[GameSlateEntry],
    env: GameEnvironment,
    description: str,
) -> None:
    """Render a tier section with its games."""
    color = ENV_COLORS[env]

    st.subheader(title)
    st.markdown(f"*{description}*")

    for game in games:
        _render_game_card(game, color)


def _render_game_card(game: GameSlateEntry, border_color: str) -> None:
    """Render a single game's analysis card."""
    time_str = ""
    if game.commence_time:
        time_str = game.commence_time.strftime("%I:%M %p ET")

    # Game header
    st.markdown(
        f'<div style="border-left: 4px solid {border_color}; '
        f'padding: 12px; margin-bottom: 16px; '
        f'background-color: rgba(255,255,255,0.03); border-radius: 4px;">'
        f"<h4 style='margin:0;'>{game.away_team} @ {game.home_team}</h4>"
        f"<small>{time_str}</small>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Vegas line
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", f"{game.total}")
    col2.metric(
        f"{_short_name(game.home_team)} ITT",
        f"{game.home_implied_total:.1f}",
    )
    col3.metric(
        f"{_short_name(game.away_team)} ITT",
        f"{game.away_implied_total:.1f}",
    )
    spread_str = f"{game.home_spread:+.1f}" if game.home_spread else "—"
    col4.metric("Spread (Home)", spread_str)

    # Moneyline
    ml_col1, ml_col2 = st.columns(2)
    ml_col1.metric(
        f"{_short_name(game.home_team)} ML",
        _format_ml(game.home_ml),
    )
    ml_col2.metric(
        f"{_short_name(game.away_team)} ML",
        _format_ml(game.away_ml),
    )

    # Shot quality comparison (if available)
    if game.home_hdcf_pct is not None or game.away_hdcf_pct is not None:
        st.markdown("**Shot Quality (5v5)**")
        sq_cols = st.columns(5)

        metrics = [
            ("HDCF%", game.home_hdcf_pct, game.away_hdcf_pct),
            ("xGF%", game.home_xgf_pct, game.away_xgf_pct),
            ("HDCF/gm", game.home_hdcf_per_60, game.away_hdcf_per_60),
            ("HDCA/gm", game.home_hdca_per_60, game.away_hdca_per_60),
            ("PDO", game.home_pdo, game.away_pdo),
        ]

        for col, (label, home_val, away_val) in zip(sq_cols, metrics):
            home_str = f"{home_val:.1f}" if home_val is not None else "—"
            away_str = f"{away_val:.1f}" if away_val is not None else "—"
            col.markdown(
                f"**{label}**\n\n"
                f"{_short_name(game.home_team)}: {home_str}\n\n"
                f"{_short_name(game.away_team)}: {away_str}"
            )

    # Line combinations (if available)
    if game.home_lines or game.away_lines:
        _render_line_combinations(game)

    # Environment classification
    if game.environment_reason:
        st.info(f"**Analysis:** {game.environment_reason}")

    # Divergence flag
    if game.divergence_flag:
        st.warning(f"**Divergence:** {game.divergence_detail}")

    st.divider()


def _short_name(team: str) -> str:
    """Get a short display name for a team.

    'Carolina Hurricanes' → 'CAR' if we can map it, otherwise last word.
    """
    from src.extract.natural_stat_trick import ODDS_API_NAME_TO_ABBREV

    abbrev = ODDS_API_NAME_TO_ABBREV.get(team)
    if abbrev:
        return abbrev
    # Fallback: last word of team name
    return team.split()[-1][:4].upper()


def _format_ml(ml: int) -> str:
    """Format moneyline for display."""
    return f"+{ml}" if ml > 0 else str(ml)


def _render_line_combinations(game: GameSlateEntry) -> None:
    """Render line combinations for both teams in a collapsible section."""
    with st.expander("Line Combinations & Goalie Confirmations", expanded=True):
        home_col, away_col = st.columns(2)

        with home_col:
            st.markdown(f"**{_short_name(game.home_team)} (Home)**")
            if game.home_lines:
                _render_team_lines(game.home_lines)
            else:
                st.caption("Line data unavailable")

        with away_col:
            st.markdown(f"**{_short_name(game.away_team)} (Away)**")
            if game.away_lines:
                _render_team_lines(game.away_lines)
            else:
                st.caption("Line data unavailable")


def _render_team_lines(lines: TeamLines) -> None:
    """Render a single team's line combinations."""
    # Starting goalie (prominent)
    if lines.starting_goalie:
        goalie_text = _format_player(lines.starting_goalie)
        st.markdown(f"**Starter:** {goalie_text}")
    if lines.backup_goalie:
        backup_text = _format_player(lines.backup_goalie)
        st.caption(f"Backup: {backup_text}")

    # Forward lines
    if lines.forward_lines:
        st.markdown("**Forwards**")
        for combo in lines.forward_lines:
            _render_combo_line(combo)

    # Defense pairs
    if lines.defense_pairs:
        st.markdown("**Defense**")
        for combo in lines.defense_pairs:
            _render_combo_line(combo)

    # Power play
    if lines.power_play:
        st.markdown("**Power Play**")
        for combo in lines.power_play:
            _render_combo_line(combo)

    # Penalty kill
    if lines.penalty_kill:
        st.markdown("**Penalty Kill**")
        for combo in lines.penalty_kill:
            _render_combo_line(combo)


def _render_combo_line(combo: LineCombination) -> None:
    """Render a single line/pair/unit as a compact string."""
    label = combo.group_id.upper()
    players_str = " — ".join(_format_player(p) for p in combo.players)
    st.caption(f"{label}: {players_str}")


def _format_player(player: PlayerLine) -> str:
    """Format a player name with injury/GTD markers."""
    name = player.name
    if player.injury_status == "out":
        return f"~~{name}~~ (OUT)"
    if player.injury_status == "dtd":
        return f"{name} (DTD)"
    if player.game_time_decision:
        return f"{name} (GTD)"
    return name


def _demo_slate() -> SlateBreakdown:
    """Generate a demo slate for display when no API key is configured."""
    # Sample line data for demo mode
    col_lines = TeamLines(
        team_abbrev="COL",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Artturi Lehkonen", position="LW"),
                    PlayerLine(name="Nathan MacKinnon", position="C"),
                    PlayerLine(name="Mikko Rantanen", position="RW"),
                ],
            ),
            LineCombination(
                group_type="ev", group_name="Forwards 2", group_id="f2",
                players=[
                    PlayerLine(name="Ross Colton", position="LW"),
                    PlayerLine(name="Casey Mittelstadt", position="C"),
                    PlayerLine(name="Valeri Nichushkin", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Devon Toews", position="LD"),
                    PlayerLine(name="Cale Makar", position="RD"),
                ],
            ),
        ],
        power_play=[
            LineCombination(
                group_type="pp", group_name="1st Powerplay Unit", group_id="pp1",
                players=[
                    PlayerLine(name="Artturi Lehkonen", position="LW"),
                    PlayerLine(name="Nathan MacKinnon", position="C"),
                    PlayerLine(name="Mikko Rantanen", position="RW"),
                    PlayerLine(name="Cale Makar", position="RD"),
                    PlayerLine(name="Devon Toews", position="LD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Mackenzie Blackwood", position="G"),
        backup_goalie=PlayerLine(name="Scott Wedgewood", position="G"),
    )

    edm_lines = TeamLines(
        team_abbrev="EDM",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Zach Hyman", position="LW"),
                    PlayerLine(name="Connor McDavid", position="C"),
                    PlayerLine(name="Leon Draisaitl", position="RW"),
                ],
            ),
            LineCombination(
                group_type="ev", group_name="Forwards 2", group_id="f2",
                players=[
                    PlayerLine(name="Ryan Nugent-Hopkins", position="LW"),
                    PlayerLine(name="Adam Henrique", position="C"),
                    PlayerLine(name="Viktor Arvidsson", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Mattias Ekholm", position="LD"),
                    PlayerLine(name="Evan Bouchard", position="RD"),
                ],
            ),
        ],
        power_play=[
            LineCombination(
                group_type="pp", group_name="1st Powerplay Unit", group_id="pp1",
                players=[
                    PlayerLine(name="Zach Hyman", position="LW"),
                    PlayerLine(name="Connor McDavid", position="C"),
                    PlayerLine(name="Leon Draisaitl", position="RW"),
                    PlayerLine(name="Evan Bouchard", position="RD"),
                    PlayerLine(name="Ryan Nugent-Hopkins", position="LW"),
                ],
            ),
        ],
        penalty_kill=[
            LineCombination(
                group_type="pk", group_name="1st Penalty Kill Unit", group_id="pk1",
                players=[
                    PlayerLine(name="Connor McDavid", position="C"),
                    PlayerLine(name="Zach Hyman", position="LW"),
                    PlayerLine(name="Mattias Ekholm", position="LD"),
                    PlayerLine(name="Evan Bouchard", position="RD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Stuart Skinner", position="G"),
        backup_goalie=PlayerLine(
            name="Calvin Pickard", position="G", injury_status="dtd",
        ),
    )

    car_lines = TeamLines(
        team_abbrev="CAR",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Seth Jarvis", position="LW"),
                    PlayerLine(name="Sebastian Aho", position="C"),
                    PlayerLine(name="Jack Roslovic", position="RW"),
                ],
            ),
            LineCombination(
                group_type="ev", group_name="Forwards 2", group_id="f2",
                players=[
                    PlayerLine(name="Andrei Svechnikov", position="LW"),
                    PlayerLine(name="Jesperi Kotkaniemi", position="C"),
                    PlayerLine(name="Martin Necas", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Jaccob Slavin", position="LD"),
                    PlayerLine(name="Brent Burns", position="RD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Frederik Andersen", position="G"),
        backup_goalie=PlayerLine(name="Pyotr Kochetkov", position="G"),
    )

    phi_lines = TeamLines(
        team_abbrev="PHI",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Travis Konecny", position="LW"),
                    PlayerLine(name="Sean Couturier", position="C"),
                    PlayerLine(name="Matvei Michkov", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Travis Sanheim", position="LD"),
                    PlayerLine(name="Cam York", position="RD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Samuel Ersson", position="G"),
        backup_goalie=PlayerLine(name="Ivan Fedotov", position="G"),
    )

    nsh_lines = TeamLines(
        team_abbrev="NSH",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Filip Forsberg", position="LW"),
                    PlayerLine(name="Ryan O'Reilly", position="C"),
                    PlayerLine(name="Gustav Nyquist", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Roman Josi", position="LD"),
                    PlayerLine(name="Alexandre Carrier", position="RD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Juuse Saros", position="G"),
        backup_goalie=PlayerLine(name="Kevin Lankinen", position="G"),
    )

    chi_lines = TeamLines(
        team_abbrev="CHI",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Connor Bedard", position="LW"),
                    PlayerLine(name="Philipp Kurashev", position="C"),
                    PlayerLine(name="Teuvo Teravainen", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Alex Vlasic", position="LD"),
                    PlayerLine(name="Connor Murphy", position="RD",
                               injury_status="dtd"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Petr Mrazek", position="G"),
        backup_goalie=PlayerLine(name="Arvid Soderblom", position="G"),
    )

    tor_lines = TeamLines(
        team_abbrev="TOR",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Matthew Knies", position="LW"),
                    PlayerLine(name="Auston Matthews", position="C"),
                    PlayerLine(name="Mitch Marner", position="RW"),
                ],
            ),
            LineCombination(
                group_type="ev", group_name="Forwards 2", group_id="f2",
                players=[
                    PlayerLine(name="Bobby McMann", position="LW"),
                    PlayerLine(name="John Tavares", position="C"),
                    PlayerLine(name="William Nylander", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Morgan Rielly", position="LD"),
                    PlayerLine(name="Chris Tanev", position="RD"),
                ],
            ),
        ],
        power_play=[
            LineCombination(
                group_type="pp", group_name="1st Powerplay Unit", group_id="pp1",
                players=[
                    PlayerLine(name="Auston Matthews", position="C"),
                    PlayerLine(name="Mitch Marner", position="RW"),
                    PlayerLine(name="William Nylander", position="LW"),
                    PlayerLine(name="John Tavares", position="C"),
                    PlayerLine(name="Morgan Rielly", position="LD"),
                ],
            ),
        ],
        penalty_kill=[
            LineCombination(
                group_type="pk", group_name="1st Penalty Kill Unit", group_id="pk1",
                players=[
                    PlayerLine(name="Auston Matthews", position="C"),
                    PlayerLine(name="Mitch Marner", position="RW"),
                    PlayerLine(name="Chris Tanev", position="RD"),
                    PlayerLine(name="Morgan Rielly", position="LD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Joseph Woll", position="G"),
        backup_goalie=PlayerLine(name="Anthony Stolarz", position="G"),
    )

    bos_lines = TeamLines(
        team_abbrev="BOS",
        forward_lines=[
            LineCombination(
                group_type="ev", group_name="Forwards 1", group_id="f1",
                players=[
                    PlayerLine(name="Brad Marchand", position="LW"),
                    PlayerLine(name="Elias Lindholm", position="C"),
                    PlayerLine(name="David Pastrnak", position="RW"),
                ],
            ),
        ],
        defense_pairs=[
            LineCombination(
                group_type="ev", group_name="Defense 1", group_id="d1",
                players=[
                    PlayerLine(name="Hampus Lindholm", position="LD"),
                    PlayerLine(name="Charlie McAvoy", position="RD"),
                ],
            ),
        ],
        starting_goalie=PlayerLine(name="Jeremy Swayman", position="G"),
        backup_goalie=PlayerLine(name="Joonas Korpisalo", position="G"),
    )

    return SlateBreakdown(
        games=[
            GameSlateEntry(
                home_team="Colorado Avalanche",
                away_team="Edmonton Oilers",
                total=6.5,
                home_implied_total=3.5,
                away_implied_total=3.0,
                home_ml=-145,
                away_ml=122,
                home_spread=-1.5,
                home_hdcf_pct=55.2,
                home_xgf_pct=54.8,
                home_hdcf_per_60=12.1,
                home_hdca_per_60=9.8,
                home_pdo=100.2,
                away_hdcf_pct=53.8,
                away_xgf_pct=52.1,
                away_hdcf_per_60=11.5,
                away_hdca_per_60=10.2,
                away_pdo=101.0,
                environment=GameEnvironment.CHALK,
                environment_reason=(
                    "High total (6.5) with strong shot quality on both sides "
                    "(home HDCF% 55.2, away HDCF% 53.8). "
                    "Expect high ownership — core game for the slate."
                ),
                home_lines=col_lines,
                away_lines=edm_lines,
            ),
            GameSlateEntry(
                home_team="Carolina Hurricanes",
                away_team="Philadelphia Flyers",
                total=5.5,
                home_implied_total=3.2,
                away_implied_total=2.3,
                home_ml=-190,
                away_ml=158,
                home_spread=-1.5,
                home_hdcf_pct=56.3,
                home_xgf_pct=55.1,
                home_hdcf_per_60=12.8,
                home_hdca_per_60=8.9,
                home_pdo=99.5,
                away_hdcf_pct=44.2,
                away_xgf_pct=45.8,
                away_hdcf_per_60=8.5,
                away_hdca_per_60=12.1,
                away_pdo=102.3,
                environment=GameEnvironment.LEVERAGE,
                environment_reason=(
                    "Total 5.5 with Carolina dominating shot quality "
                    "(HDCF% 56.3 vs 44.2). "
                    "Home stacks are the play — the quality edge is real."
                ),
                divergence_flag=True,
                divergence_detail=(
                    "Philadelphia Flyers: 2.3 implied total "
                    "but only 44.2% HDCF — market overpricing offense; "
                    "Philadelphia Flyers: PDO at 102.3 — running hot, regression risk"
                ),
                home_lines=car_lines,
                away_lines=phi_lines,
            ),
            GameSlateEntry(
                home_team="Nashville Predators",
                away_team="Chicago Blackhawks",
                total=5.0,
                home_implied_total=2.8,
                away_implied_total=2.2,
                home_ml=-155,
                away_ml=130,
                home_spread=-1.5,
                home_hdcf_pct=48.1,
                home_xgf_pct=47.5,
                home_hdcf_per_60=9.2,
                home_hdca_per_60=10.0,
                home_pdo=99.1,
                away_hdcf_pct=45.3,
                away_xgf_pct=44.2,
                away_hdcf_per_60=8.1,
                away_hdca_per_60=11.2,
                away_pdo=98.0,
                environment=GameEnvironment.AVOID,
                environment_reason=(
                    "Low total (5.0) with weak shot quality on both sides "
                    "(home HDCF% 48.1, away HDCF% 45.3). No edge."
                ),
                home_lines=nsh_lines,
                away_lines=chi_lines,
            ),
            GameSlateEntry(
                home_team="Toronto Maple Leafs",
                away_team="Boston Bruins",
                total=5.5,
                home_implied_total=2.9,
                away_implied_total=2.6,
                home_ml=-130,
                away_ml=110,
                home_spread=-1.5,
                home_hdcf_pct=51.2,
                home_xgf_pct=50.8,
                home_hdcf_per_60=10.5,
                home_hdca_per_60=10.0,
                home_pdo=100.8,
                away_hdcf_pct=49.1,
                away_xgf_pct=49.5,
                away_hdcf_per_60=10.1,
                away_hdca_per_60=10.3,
                away_pdo=99.2,
                environment=GameEnvironment.CONTRARIAN,
                environment_reason=(
                    "Low total (5.5) but home team has strong shot quality. "
                    "Low ownership = GPP upside."
                ),
                home_lines=tor_lines,
                away_lines=bos_lines,
            ),
        ]
    )
