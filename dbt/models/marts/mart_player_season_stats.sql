with skater_stats as (
    select * from {{ ref('stg_skater_stats') }}
),

players as (
    select * from {{ ref('stg_players') }}
)

select
    ss.player_id,
    ss.season_id,
    p.full_name,
    p.team_abbrev,
    p.team_full_name,
    p.position,
    count(*) as games_played,
    sum(ss.goals) as goals,
    sum(ss.assists) as assists,
    sum(ss.points) as points,
    sum(ss.shots) as shots,
    sum(ss.hits) as hits,
    sum(ss.pim) as pim,
    sum(ss.plus_minus) as plus_minus,
    sum(ss.power_play_goals) as power_play_goals,
    sum(ss.power_play_points) as power_play_points,
    sum(ss.shorthanded_goals) as shorthanded_goals,
    round(avg(ss.points_per_60), 2) as avg_points_per_60,
    sum(ss.toi_seconds) as total_toi_seconds,
    round(sum(ss.toi_seconds) / 60.0, 2) as total_toi_minutes
from skater_stats ss
left join players p on ss.player_id = p.player_id
group by
    ss.player_id,
    ss.season_id,
    p.full_name,
    p.team_abbrev,
    p.team_full_name,
    p.position
