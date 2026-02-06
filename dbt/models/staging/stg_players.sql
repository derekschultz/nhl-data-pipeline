with players as (
    select * from {{ source('nhl_raw', 'dim_player') }}
),

teams as (
    select * from {{ source('nhl_raw', 'dim_team') }}
)

select
    p.player_id,
    p.first_name,
    p.last_name,
    p.first_name || ' ' || p.last_name as full_name,
    p.position,
    p.team_abbrev,
    t.full_name as team_full_name,
    t.division,
    t.conference,
    p.jersey_number,
    p.shoots_catches,
    p.birth_date
from players p
left join teams t on p.team_abbrev = t.team_abbrev
where p.position in ('C', 'LW', 'RW', 'D', 'G')
