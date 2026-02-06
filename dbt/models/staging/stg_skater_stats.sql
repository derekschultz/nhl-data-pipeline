with skater_stats as (
    select * from {{ source('nhl_raw', 'fact_game_skater_stats') }}
),

games as (
    select * from {{ source('nhl_raw', 'dim_game') }}
)

select
    ss.player_id,
    ss.game_id,
    ss.team_abbrev,
    g.game_date,
    g.season_id,
    ss.goals,
    ss.assists,
    ss.points,
    ss.shots,
    ss.hits,
    ss.blocked_shots,
    ss.pim,
    ss.toi_seconds,
    round(ss.toi_seconds / 60.0, 2) as toi_minutes,
    ss.plus_minus,
    ss.power_play_goals,
    ss.power_play_points,
    ss.shorthanded_goals,
    ss.faceoff_pct,
    case
        when ss.toi_seconds > 0
        then round((ss.points * 3600.0) / ss.toi_seconds, 2)
        else 0
    end as points_per_60
from skater_stats ss
left join games g on ss.game_id = g.game_id
