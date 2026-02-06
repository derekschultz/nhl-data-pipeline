with games as (
    select * from {{ ref('stg_games') }}
),

home_results as (
    select
        home_team as team_abbrev,
        season_id,
        count(*) as home_games,
        sum(case when is_home_win then 1 else 0 end) as home_wins,
        sum(case when not is_home_win then 1 else 0 end) as home_losses
    from games
    group by home_team, season_id
),

away_results as (
    select
        away_team as team_abbrev,
        season_id,
        count(*) as away_games,
        sum(case when not is_home_win then 1 else 0 end) as away_wins,
        sum(case when is_home_win then 1 else 0 end) as away_losses
    from games
    group by away_team, season_id
),

ot_losses as (
    select
        losing_team as team_abbrev,
        season_id,
        count(*) as otl
    from games
    where goal_differential = 1
    group by losing_team, season_id
)

select
    coalesce(h.team_abbrev, a.team_abbrev) as team_abbrev,
    coalesce(h.season_id, a.season_id) as season_id,
    coalesce(h.home_games, 0) + coalesce(a.away_games, 0) as games_played,
    coalesce(h.home_wins, 0) + coalesce(a.away_wins, 0) as wins,
    coalesce(h.home_losses, 0) + coalesce(a.away_losses, 0)
        - coalesce(o.otl, 0) as losses,
    coalesce(o.otl, 0) as otl,
    (coalesce(h.home_wins, 0) + coalesce(a.away_wins, 0)) * 2
        + coalesce(o.otl, 0) as points,
    case
        when coalesce(h.home_games, 0) + coalesce(a.away_games, 0) > 0
        then round(
            ((coalesce(h.home_wins, 0) + coalesce(a.away_wins, 0)) * 2.0
                + coalesce(o.otl, 0))
            / ((coalesce(h.home_games, 0) + coalesce(a.away_games, 0)) * 2.0),
            3
        )
        else 0
    end as win_pct,
    coalesce(h.home_wins, 0) as home_wins,
    coalesce(h.home_losses, 0) as home_losses,
    coalesce(a.away_wins, 0) as away_wins,
    coalesce(a.away_losses, 0) as away_losses
from home_results h
full outer join away_results a
    on h.team_abbrev = a.team_abbrev and h.season_id = a.season_id
left join ot_losses o
    on coalesce(h.team_abbrev, a.team_abbrev) = o.team_abbrev
    and coalesce(h.season_id, a.season_id) = o.season_id
