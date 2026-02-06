with goalie_stats as (
    select * from {{ ref('stg_goalie_stats') }}
),

players as (
    select * from {{ ref('stg_players') }}
)

select
    gs.player_id,
    gs.season_id,
    p.full_name,
    p.team_abbrev,
    p.team_full_name,
    count(*) as games_played,
    sum(case when gs.decision = 'W' then 1 else 0 end) as wins,
    sum(case when gs.decision = 'L' then 1 else 0 end) as losses,
    sum(case when gs.decision = 'O' then 1 else 0 end) as otl,
    sum(gs.saves) as total_saves,
    sum(gs.shots_against) as total_shots_against,
    case
        when sum(gs.shots_against) > 0
        then round(sum(gs.saves)::numeric / sum(gs.shots_against), 3)
        else 0
    end as save_pct,
    case
        when sum(gs.toi_seconds) > 0
        then round((sum(gs.goals_against) * 3600.0) / sum(gs.toi_seconds), 2)
        else 0
    end as goals_against_average,
    sum(gs.toi_seconds) as total_toi_seconds,
    sum(case when gs.is_quality_start then 1 else 0 end) as quality_starts,
    case
        when count(*) > 0
        then round(
            sum(case when gs.is_quality_start then 1 else 0 end)::numeric / count(*),
            3
        )
        else 0
    end as quality_start_pct
from goalie_stats gs
left join players p on gs.player_id = p.player_id
group by
    gs.player_id,
    gs.season_id,
    p.full_name,
    p.team_abbrev,
    p.team_full_name
