-- Seed data: NHL teams for the 2025-2026 season

INSERT INTO dim_team (team_abbrev, full_name, division, conference) VALUES
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
ON CONFLICT (team_abbrev) DO NOTHING;

INSERT INTO dim_season (season_id, start_year, end_year, season_type) VALUES
    ('20252026', 2025, 2026, 'regular')
ON CONFLICT (season_id) DO NOTHING;
