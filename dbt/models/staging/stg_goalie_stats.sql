with goalie_stats as (
    select * from {{ source('nhl_raw', 'fact_game_goalie_stats') }}
),

games as (
    select * from {{ source('nhl_raw', 'dim_game') }}
)

select
    gs.player_id,
    gs.game_id,
    gs.team_abbrev,
    g.game_date,
    g.season_id,
    gs.decision,
    gs.shots_against,
    gs.saves,
    gs.goals_against,
    gs.toi_seconds,
    round(gs.toi_seconds / 60.0, 2) as toi_minutes,
    gs.save_pct,
    gs.power_play_saves,
    gs.shorthanded_saves,
    gs.even_strength_saves,
    case
        when gs.save_pct >= 0.920 and gs.decision = 'W'
        then true
        else false
    end as is_quality_start
from goalie_stats gs
left join games g on gs.game_id = g.game_id
