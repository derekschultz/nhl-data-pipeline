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
        ('UTA', 'Utah Mammoth', 'Central', 'Western'),
        ('VAN', 'Vancouver Canucks', 'Pacific', 'Western'),
        ('VGK', 'Vegas Golden Knights', 'Pacific', 'Western'),
        ('WPG', 'Winnipeg Jets', 'Central', 'Western'),
        ('WSH', 'Washington Capitals', 'Metropolitan', 'Eastern')
) AS source
ON target.team_abbrev = source.team_abbrev
WHEN NOT MATCHED THEN
    INSERT (team_abbrev, full_name, division, conference)
    VALUES (source.team_abbrev, source.full_name, source.division, source.conference);

-- Seed seasons (historical + current)
MERGE INTO dim_season AS target
USING (
    SELECT column1 AS season_id, column2 AS start_year, column3 AS end_year, column4 AS season_type
    FROM VALUES
        ('20202021', 2020, 2021, 'regular'),
        ('20212022', 2021, 2022, 'regular'),
        ('20222023', 2022, 2023, 'regular'),
        ('20232024', 2023, 2024, 'regular'),
        ('20242025', 2024, 2025, 'regular'),
        ('20252026', 2025, 2026, 'regular')
) AS source
ON target.season_id = source.season_id
WHEN NOT MATCHED THEN
    INSERT (season_id, start_year, end_year, season_type)
    VALUES (source.season_id, source.start_year, source.end_year, source.season_type);
