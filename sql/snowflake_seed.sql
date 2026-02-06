-- Seed data: NHL teams for the 2025-2026 season (Snowflake)
-- Snowflake does not support ON CONFLICT, so we use MERGE for idempotency.

USE SCHEMA NHL.PUBLIC;

-- Seed teams using MERGE for idempotent inserts
MERGE INTO dim_team AS target
USING (
    SELECT column1 AS team_abbrev, column2 AS full_name, column3 AS division, column4 AS conference
    FROM VALUES
        ('ANA', 'Anaheim Ducks', 'Pacific', 'Western'),
        ('BOS', 'Boston Bruins', 'Atlantic', 'Eastern'),
        ('BUF', 'Buffalo Sabres', 'Atlantic', 'Eastern'),
        ('CAR', 'Carolina Hurricanes', 'Metropolitan', 'Eastern'),
        ('CBJ', 'Columbus Blue Jackets', 'Metropolitan', 'Eastern'),
        ('CGY', 'Calgary Flames', 'Pacific', 'Western'),
        ('CHI', 'Chicago Blackhawks', 'Central', 'Western'),
        ('COL', 'Colorado Avalanche', 'Central', 'Western'),
        ('DAL', 'Dallas Stars', 'Central', 'Western'),
        ('DET', 'Detroit Red Wings', 'Atlantic', 'Eastern'),
        ('EDM', 'Edmonton Oilers', 'Pacific', 'Western'),
        ('FLA', 'Florida Panthers', 'Atlantic', 'Eastern'),
        ('LAK', 'Los Angeles Kings', 'Pacific', 'Western'),
        ('MIN', 'Minnesota Wild', 'Central', 'Western'),
        ('MTL', 'Montreal Canadiens', 'Atlantic', 'Eastern'),
        ('NJD', 'New Jersey Devils', 'Metropolitan', 'Eastern'),
        ('NSH', 'Nashville Predators', 'Central', 'Western'),
        ('NYI', 'New York Islanders', 'Metropolitan', 'Eastern'),
        ('NYR', 'New York Rangers', 'Metropolitan', 'Eastern'),
        ('OTT', 'Ottawa Senators', 'Atlantic', 'Eastern'),
        ('PHI', 'Philadelphia Flyers', 'Metropolitan', 'Eastern'),
        ('PIT', 'Pittsburgh Penguins', 'Metropolitan', 'Eastern'),
        ('SEA', 'Seattle Kraken', 'Pacific', 'Western'),
        ('SJS', 'San Jose Sharks', 'Pacific', 'Western'),
        ('STL', 'St. Louis Blues', 'Central', 'Western'),
        ('TBL', 'Tampa Bay Lightning', 'Atlantic', 'Eastern'),
        ('TOR', 'Toronto Maple Leafs', 'Atlantic', 'Eastern'),
        ('UTA', 'Utah Hockey Club', 'Central', 'Western'),
        ('VAN', 'Vancouver Canucks', 'Pacific', 'Western'),
        ('VGK', 'Vegas Golden Knights', 'Pacific', 'Western'),
        ('WPG', 'Winnipeg Jets', 'Central', 'Western'),
        ('WSH', 'Washington Capitals', 'Metropolitan', 'Eastern')
) AS source
ON target.team_abbrev = source.team_abbrev
WHEN NOT MATCHED THEN
    INSERT (team_abbrev, full_name, division, conference)
    VALUES (source.team_abbrev, source.full_name, source.division, source.conference);

-- Seed season
MERGE INTO dim_season AS target
USING (
    SELECT '20252026' AS season_id, 2025 AS start_year, 2026 AS end_year, 'regular' AS season_type
) AS source
ON target.season_id = source.season_id
WHEN NOT MATCHED THEN
    INSERT (season_id, start_year, end_year, season_type)
    VALUES (source.season_id, source.start_year, source.end_year, source.season_type);
