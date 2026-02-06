"""Streamlit dashboard for exploring NHL stats.

Works progressively: shows seed data (32 teams) immediately,
and displays richer analytics as ETL + dbt populate the database.
"""

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

st.set_page_config(page_title="NHL Data Pipeline", layout="wide")


@st.cache_resource
def get_engine() -> Engine:
    """Create a SQLAlchemy engine from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "nhl")
    user = os.getenv("POSTGRES_USER", "nhl")
    password = os.getenv("POSTGRES_PASSWORD", "nhl")
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


def safe_query(_engine: Engine, query: str) -> pd.DataFrame | None:
    """Execute a query and return a DataFrame, or None on error."""
    try:
        return pd.read_sql(text(query), _engine)
    except Exception:
        return None


def table_exists(_engine: Engine, table_name: str) -> bool:
    """Check if a table or view exists in the public schema."""
    df = safe_query(
        _engine,
        f"SELECT 1 FROM information_schema.tables "
        f"WHERE table_schema = 'public' AND table_name = '{table_name}' LIMIT 1",
    )
    return df is not None and len(df) > 0


def row_count(_engine: Engine, table_name: str) -> int:
    """Return row count for a table, or 0 if it doesn't exist."""
    if not table_exists(_engine, table_name):
        return 0
    df = safe_query(_engine, f"SELECT COUNT(*) AS cnt FROM {table_name}")
    if df is not None and len(df) > 0:
        return int(df["cnt"].iloc[0])
    return 0


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_overview(_engine: Engine) -> None:
    """Overview page with record counts and pipeline status."""
    st.header("Pipeline Overview")

    tables = [
        "dim_season", "dim_team", "dim_player",
        "dim_game", "fact_game_skater_stats", "fact_game_goalie_stats",
    ]
    counts = {t: row_count(_engine, t) for t in tables}

    cols = st.columns(len(tables))
    for col, table in zip(cols, tables):
        label = table.replace("dim_", "").replace("fact_game_", "").replace("_", " ").title()
        col.metric(label, f"{counts[table]:,}")

    has_game_data = counts["dim_game"] > 0

    if not has_game_data:
        st.info(
            "Seed data loaded. Run the ETL pipeline to populate game and player data.\n\n"
            "```bash\nmake pipeline\n```"
        )

    # Pipeline runs
    st.subheader("Recent Pipeline Runs")
    if table_exists(_engine, "pipeline_runs"):
        runs = safe_query(
            _engine,
            "SELECT run_id, run_date, started_at, completed_at, status, "
            "rows_extracted, rows_loaded, error_message "
            "FROM pipeline_runs ORDER BY started_at DESC LIMIT 5",
        )
        if runs is not None and len(runs) > 0:
            st.dataframe(runs, use_container_width=True, hide_index=True)
        else:
            st.info("No pipeline runs recorded yet.")
    else:
        st.info("No pipeline runs recorded yet.")

    # Mart availability
    st.subheader("dbt Mart Availability")
    marts = ["mart_team_standings", "mart_player_season_stats", "mart_goalie_rankings"]
    mart_cols = st.columns(len(marts))
    for col, mart in zip(mart_cols, marts):
        exists = table_exists(_engine, mart)
        label = mart.replace("mart_", "").replace("_", " ").title()
        col.metric(label, "Available" if exists else "Not built")

    if not any(table_exists(_engine, m) for m in marts):
        st.info(
            "dbt marts have not been built yet. Run dbt to create analytics tables:\n\n"
            "```bash\nmake dbt-run\n```"
        )


def page_teams(_engine: Engine) -> None:
    """Teams page - works with seed data alone."""
    st.header("NHL Teams")

    df = safe_query(
        _engine,
        "SELECT team_abbrev, full_name, division, conference "
        "FROM dim_team ORDER BY conference, division, full_name",
    )
    if df is None or len(df) == 0:
        st.warning("No team data found. Ensure the database is seeded.")
        return

    st.metric("Total Teams", len(df))

    for conference in sorted(df["conference"].unique()):
        st.subheader(f"{conference} Conference")
        conf_df = df[df["conference"] == conference]
        div_cols = st.columns(len(conf_df["division"].unique()))
        for col, division in zip(div_cols, sorted(conf_df["division"].unique())):
            div_df = conf_df[conf_df["division"] == division]
            col.markdown(f"**{division}**")
            for _, row in div_df.iterrows():
                col.markdown(f"- {row['team_abbrev']} — {row['full_name']}")


def page_standings(_engine: Engine) -> None:
    """Team standings from mart or fallback to raw game counts."""
    st.header("Team Standings")

    if table_exists(_engine, "mart_team_standings"):
        df = safe_query(
            _engine,
            "SELECT * FROM mart_team_standings ORDER BY points DESC",
        )
        if df is not None and len(df) > 0:
            st.dataframe(df, use_container_width=True, hide_index=True)
            return

    # Fallback: count games per team from dim_game
    if row_count(_engine, "dim_game") == 0:
        st.info(
            "No game data available yet. Run the ETL pipeline to load games.\n\n"
            "```bash\nmake pipeline\n```"
        )
        return

    st.warning("dbt mart not built. Showing simplified game counts from raw data.")
    df = safe_query(
        _engine,
        """
        SELECT t.team_abbrev, t.full_name,
               COUNT(DISTINCT g.game_id) AS games
        FROM dim_team t
        LEFT JOIN dim_game g ON t.team_abbrev = g.home_team OR t.team_abbrev = g.away_team
        WHERE g.game_id IS NOT NULL
        GROUP BY t.team_abbrev, t.full_name
        ORDER BY games DESC
        """,
    )
    if df is not None and len(df) > 0:
        st.dataframe(df, use_container_width=True, hide_index=True)


def page_player_stats(_engine: Engine) -> None:
    """Player stats from mart or fallback to raw aggregation."""
    st.header("Player Stats")

    use_mart = table_exists(_engine, "mart_player_season_stats")

    if use_mart:
        source_query = "SELECT * FROM mart_player_season_stats"
    elif row_count(_engine, "fact_game_skater_stats") > 0:
        st.warning("dbt mart not built. Showing aggregated raw stats.")
        source_query = """
            SELECT p.player_id, p.first_name, p.last_name,
                   p.position, p.team_abbrev,
                   COUNT(*) AS games_played,
                   SUM(s.goals) AS goals, SUM(s.assists) AS assists,
                   SUM(s.points) AS points, SUM(s.shots) AS shots,
                   SUM(s.hits) AS hits
            FROM fact_game_skater_stats s
            JOIN dim_player p ON s.player_id = p.player_id
            GROUP BY p.player_id, p.first_name, p.last_name, p.position, p.team_abbrev
        """
    else:
        st.info(
            "No player stats available yet. Run the ETL pipeline to load game data.\n\n"
            "```bash\nmake pipeline\n```"
        )
        return

    df = safe_query(_engine, source_query)
    if df is None or len(df) == 0:
        st.info("No player stats found.")
        return

    # Filters
    filter_cols = st.columns(3)
    teams = sorted(df["team_abbrev"].dropna().unique())
    selected_team = filter_cols[0].selectbox("Team", ["All"] + teams)

    if "position" in df.columns:
        positions = sorted(df["position"].dropna().unique())
        selected_pos = filter_cols[1].selectbox("Position", ["All"] + positions)
    else:
        selected_pos = "All"

    if "games_played" in df.columns:
        min_gp = filter_cols[2].number_input("Min Games Played", min_value=0, value=0, step=1)
    else:
        min_gp = 0

    filtered = df.copy()
    if selected_team != "All":
        filtered = filtered[filtered["team_abbrev"] == selected_team]
    if selected_pos != "All" and "position" in filtered.columns:
        filtered = filtered[filtered["position"] == selected_pos]
    if min_gp > 0 and "games_played" in filtered.columns:
        filtered = filtered[filtered["games_played"] >= min_gp]

    sort_col = "points" if "points" in filtered.columns else filtered.columns[0]
    filtered = filtered.sort_values(sort_col, ascending=False)

    st.dataframe(filtered, use_container_width=True, hide_index=True)


def page_goalie_rankings(_engine: Engine) -> None:
    """Goalie rankings from mart or fallback to raw aggregation."""
    st.header("Goalie Rankings")

    use_mart = table_exists(_engine, "mart_goalie_rankings")

    if use_mart:
        source_query = "SELECT * FROM mart_goalie_rankings"
    elif row_count(_engine, "fact_game_goalie_stats") > 0:
        st.warning("dbt mart not built. Showing aggregated raw stats.")
        source_query = """
            SELECT p.player_id, p.first_name, p.last_name,
                   p.team_abbrev,
                   COUNT(*) AS games_played,
                   SUM(g.saves) AS saves,
                   SUM(g.shots_against) AS shots_against,
                   SUM(g.goals_against) AS goals_against,
                   CASE WHEN SUM(g.shots_against) > 0
                        THEN ROUND(SUM(g.saves)::numeric / SUM(g.shots_against), 3)
                        ELSE NULL END AS save_pct
            FROM fact_game_goalie_stats g
            JOIN dim_player p ON g.player_id = p.player_id
            GROUP BY p.player_id, p.first_name, p.last_name, p.team_abbrev
        """
    else:
        st.info(
            "No goalie stats available yet. Run the ETL pipeline to load game data.\n\n"
            "```bash\nmake pipeline\n```"
        )
        return

    df = safe_query(_engine, source_query)
    if df is None or len(df) == 0:
        st.info("No goalie stats found.")
        return

    # Filters
    filter_cols = st.columns(2)
    teams = sorted(df["team_abbrev"].dropna().unique())
    selected_team = filter_cols[0].selectbox("Team", ["All"] + teams, key="goalie_team")

    if "games_played" in df.columns:
        min_gp = filter_cols[1].number_input(
            "Min Games Played", min_value=0, value=5, step=1, key="goalie_min_gp"
        )
    else:
        min_gp = 0

    filtered = df.copy()
    if selected_team != "All":
        filtered = filtered[filtered["team_abbrev"] == selected_team]
    if min_gp > 0 and "games_played" in filtered.columns:
        filtered = filtered[filtered["games_played"] >= min_gp]

    sort_col = "save_pct" if "save_pct" in filtered.columns else filtered.columns[0]
    filtered = filtered.sort_values(sort_col, ascending=False)

    st.dataframe(filtered, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

PAGES = {
    "Overview": page_overview,
    "Teams": page_teams,
    "Team Standings": page_standings,
    "Player Stats": page_player_stats,
    "Goalie Rankings": page_goalie_rankings,
}


def main() -> None:
    """Dashboard entry point."""
    st.title("NHL Data Pipeline Dashboard")

    engine = get_engine()

    # Connection test
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        st.error(
            f"Cannot connect to PostgreSQL: {exc}\n\n"
            "Make sure the database is running:\n\n"
            "```bash\ndocker compose up -d\n```"
        )
        st.stop()

    page = st.sidebar.radio("Navigation", list(PAGES.keys()))
    PAGES[page](engine)


main()
