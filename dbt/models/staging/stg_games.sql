with games as (
    select * from {{ source('nhl_raw', 'dim_game') }}
),

seasons as (
    select * from {{ source('nhl_raw', 'dim_season') }}
)

select
    g.game_id,
    g.season_id,
    s.start_year,
    s.end_year,
    s.season_type,
    g.game_type,
    g.game_date,
    g.home_team,
    g.away_team,
    g.home_score,
    g.away_score,
    g.venue,
    g.game_state,
    case
        when g.home_score > g.away_score then g.home_team
        when g.away_score > g.home_score then g.away_team
    end as winning_team,
    case
        when g.home_score > g.away_score then g.away_team
        when g.away_score > g.home_score then g.home_team
    end as losing_team,
    g.home_score > g.away_score as is_home_win,
    abs(g.home_score - g.away_score) as goal_differential
from games g
left join seasons s on g.season_id = s.season_id
where g.game_state = 'FINAL'
