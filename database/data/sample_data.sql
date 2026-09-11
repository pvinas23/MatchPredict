-- Sample data for testing schema.sql
INSERT INTO leagues (name, country, tier)
VALUES (
    "Premier League",
    "England",
    1
);

INSERT INTO seasons (league_id, name)
VALUES (
    1,
    "2024/2025"
);

INSERT INTO teams (name)
VALUES 
    ("Brighton"),
    ("Manchester City"),
    ("New Castle");

INSERT INTO matches (
    season_id,
    date,
    home_team_id,
    away_team_id,
    home_team_goals,
    away_team_goals,
    result,
    referee)
VALUES
    (1, '2024-08-17 15:00:00', 1, 2, 2, 1, 'H', NULL),
    (1, '2024-08-17 17:30:00', 1, 3, 1, 1, 'D', NULL),
    (1, '2024-08-24 15:00:00', 2, 3, 0, 2, 'A', NULL),
    (1, '2024-08-24 17:30:00', 3, 1, 1, 3, 'A', NULL);

INSERT INTO match_stats (match_id,
    home_shots,
    away_shots,
    home_corners,
    away_corners,
    home_yellow,
    away_yellow
)
VALUES
    (1, 15, 8, 7, 4, 1, 2),
    (2, 12, 10, 5, 5, 0, 1),
    (3, 9, 14, 3, 6, 2, 0),
    (4, 11, 18, 4, 8, 1, 1);


































-- ============================================
-- 1. INSERT leagues (no dependencies)
-- ============================================
-- INSERT INTO leagues (name, country, tier) VALUES
-- ('Premier League', 'England', 1);

-- ============================================
-- 2. INSERT seasons (depends on leagues)
-- ============================================
-- INSERT INTO seasons (league_id, name) VALUES
-- (1, '2024/2025');

-- ============================================
-- 3. INSERT teams (no dependencies)
-- ============================================
-- INSERT INTO teams (name) VALUES
-- ('Team A'),
-- ('Team B'),
-- ('Team C'),
-- ('Team D');

-- ============================================
-- 4. INSERT matches (depends on seasons, teams)
-- ============================================
-- INSERT INTO matches (season_id, date, home_team_id, away_team_id, home_team_goals, away_team_goals, result) VALUES
-- (1, '2024-08-17 15:00:00', 1, 2, 2, 1, 'H'),
-- (1, '2024-08-17 17:30:00', 3, 4, 1, 1, 'D'),
-- (1, '2024-08-24 15:00:00', 2, 3, 0, 2, 'A'),
-- (1, '2024-08-24 17:30:00', 4, 1, 1, 3, 'A');

-- ============================================
-- 5. INSERT match_stats (depends on matches)
-- ============================================
-- INSERT INTO match_stats (match_id, home_shots, away_shots, home_corners, away_corners, home_yellow, away_yellow) VALUES
-- (1, 15, 8, 7, 4, 1, 2),
-- (2, 12, 10, 5, 5, 0, 1),
-- (3, 9, 14, 3, 6, 2, 0),
-- (4, 11, 18, 4, 8, 1, 1);

-- ============================================
-- OPTIONAL: Add market odds, ratings, predictions if you want to test those tables
-- ============================================
