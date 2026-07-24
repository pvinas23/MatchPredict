-- MatchPredict Database Schema
-- Target Engine: MySQL 8.0+
-- Description: Relational structure for MatchPredict project

-- Drop existing views and tables in reverse dependency order to avoid FK errors
DROP VIEW IF EXISTS v_team_stats;
DROP VIEW IF EXISTS v_match_analytics;
DROP VIEW IF EXISTS v_match_results;
DROP TABLE IF EXISTS predicted_top_scores;
DROP TABLE IF EXISTS predictions_summary;
DROP TABLE IF EXISTS match_market_odds;
DROP TABLE IF EXISTS team_ratings;
DROP TABLE IF EXISTS match_stats;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS seasons;
DROP TABLE IF EXISTS leagues;

-- 1. We define the core tables of the project.

-- Although we only use the Premier League we create leagues table for scalability
CREATE TABLE leagues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,  -- "Premier League"
    country VARCHAR(100) NOT NULL,  -- "England"
    tier INT NOT NULL DEFAULT 1 -- 1=First division
);

CREATE TABLE seasons(
    id INT AUTO_INCREMENT PRIMARY KEY,
    league_id INT NOT NULL,
    name VARCHAR(9) NOT NULL,  -- Y/Y, like 2024/2025
    UNIQUE (league_id, name),
    CONSTRAINT fk_seasons_league
        FOREIGN KEY (league_id)
        REFERENCES leagues(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Teams are kept as a stable catalogue so the same club can be reused across
-- seasons without duplicating the base entity.
CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    season_id INT NOT NULL,
    date DATETIME NOT NULL,  -- 'YYYY-MM-DD hh:mm:ss'
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    home_team_goals INT NOT NULL CHECK (home_team_goals >= 0),
    away_team_goals INT NOT NULL CHECK (away_team_goals >= 0),
    result VARCHAR(1) NOT NULL CHECK (result IN ('H', 'D', 'A')),  -- H=home win, D=draw, A=away win
    referee VARCHAR(100) NULL,
    -- Prevent duplicate fixtures.
    CONSTRAINT uq_matches UNIQUE (season_id, date, home_team_id, away_team_id),
    CONSTRAINT ck_matches_home_away_different CHECK (home_team_id <> away_team_id),
    CONSTRAINT fk_matches_season
        FOREIGN KEY (season_id)
        REFERENCES seasons(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_matches_home_team
        FOREIGN KEY (home_team_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_matches_away_team
        FOREIGN KEY (away_team_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Match-level statistics are separated to keep the core match table light.
-- If some columns are absent in the source CSV, the ETL can stage and clean
-- them before inserting into this table.
CREATE TABLE match_stats (
    match_id INT PRIMARY KEY,
    home_shots INT,    /* HS */
    home_shots_on_target INT,  /* HST */
    home_shots_hit_woodwork INT,  /* HSW */
    home_corners INT,  /* HC */
    home_fouls_committed INT,  /* HF */
    home_free_kicks_conceded INT,  /* HFKC */
    home_offsides INT, /* HO */
    home_yellow INT,   /* HY */
    home_red INT,  /* HR */
    away_shots INT,    /* AS */
    away_shots_on_target INT, /* AST */
    away_shots_hit_woodwork INT,  /* ASW */
    away_corners INT, /* AC */
    away_fouls_committed INT,  /* AF */
    away_free_kicks_conceded INT,  /* AFKC */
    away_offsides INT, /* AO */
    away_yellow INT,   /* AY */
    away_red INT,   /* AR */
    CONSTRAINT fk_match_stats_match
        FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Ratings are derived over time, so the table needs season context as well.
CREATE TABLE team_ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    season_id INT NOT NULL,
    date DATETIME NOT NULL,
    rating DECIMAL(5, 2) NOT NULL,
    CONSTRAINT uq_team_ratings UNIQUE (team_id, season_id, date),
    CONSTRAINT fk_team_ratings_team
        FOREIGN KEY (team_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_team_ratings_season
        FOREIGN KEY (season_id)
        REFERENCES seasons(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Market odds are pre-match information, so they belong in their own table.
-- This keeps the model pipeline honest: the main Random Forest can use these
-- odds as a benchmark or optional feature set, but they stay logically separate
-- from post-match statistics such as shots or corners.
CREATE TABLE match_market_odds (
    match_id INT PRIMARY KEY,
    b365_home_win_odds DECIMAL(8, 3) NULL,
    b365_draw_odds DECIMAL(8, 3) NULL,
    b365_away_win_odds DECIMAL(8, 3) NULL,
    market_avg_home_win_odds DECIMAL(8, 3) NULL,
    market_avg_draw_odds DECIMAL(8, 3) NULL,
    market_avg_away_win_odds DECIMAL(8, 3) NULL,
    CONSTRAINT fk_match_market_odds_match
        FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- 2. We create tables to store the data created by the model.
CREATE TABLE predictions_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    prob_home_win DECIMAL(5,4) NOT NULL CHECK(prob_home_win BETWEEN 0 AND 1),
    prob_draw DECIMAL(5,4) NOT NULL CHECK(prob_draw BETWEEN 0 AND 1),
    prob_away_win DECIMAL(5,4) NOT NULL CHECK(prob_away_win BETWEEN 0 AND 1),
    CONSTRAINT uq_match_prediction UNIQUE (match_id, model_name),
    CONSTRAINT fk_predictions_summary_match
        FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE predicted_top_scores (
    match_id INT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    rank_order INT NOT NULL,
    home_goals INT NOT NULL,
    away_goals INT NOT NULL,
    probability DECIMAL(5,4) NOT NULL CHECK(probability BETWEEN 0 AND 1),
    CONSTRAINT pk_predicted_top_scores PRIMARY KEY (match_id, model_name, rank_order),
    CONSTRAINT fk_predicted_top_scores_match
        FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);




-- 3. We create indexes to make queries faster.

-- To accelerate time-based queries.
CREATE INDEX idx_matches_date ON matches(date);
CREATE INDEX idx_team_ratings_date ON team_ratings(date);
CREATE INDEX idx_team_ratings_season ON team_ratings(season_id);

-- Compound indexes between teams help head-to-head lookups.
CREATE INDEX idx_matches_head_to_head_home_away ON matches(home_team_id, away_team_id);
CREATE INDEX idx_matches_head_to_head_away_home ON matches(away_team_id, home_team_id);
CREATE INDEX idx_matches_season ON matches(season_id);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);


-- 3. We create views

-- Head-to-head between team A and team B.
-- The view uses the stored result column instead of recomputing the winner.
CREATE VIEW v_match_results AS
SELECT 
    m.id AS match_id,
    m.date,
    s.name AS season,
    th.name AS home_team,
    ta.name AS away_team,
    m.home_team_goals AS home_goals,
    m.away_team_goals AS away_goals,
    m.result AS victory
FROM matches AS m
JOIN seasons AS s ON m.season_id = s.id
JOIN teams AS th ON m.home_team_id = th.id
JOIN teams AS ta ON m.away_team_id = ta.id;

-- Statistics of a particular match.
CREATE VIEW v_match_analytics AS
SELECT
    mr.match_id AS match_id,
    mr.date AS match_date,
    mr.season AS season,
    mr.home_team AS home_team,
    mr.home_goals AS home_goals,
    ms.home_shots AS home_shots,
    ms.home_shots_on_target AS home_shots_on_target,
    ms.home_corners AS home_corners,
    ms.home_fouls_committed AS home_fouls_committed,
    ms.home_free_kicks_conceded AS home_free_kicks_conceded,
    ms.home_offsides AS home_offsides,
    ms.home_yellow AS home_yellow,
    ms.home_red AS home_red,
    mr.away_team AS away_team,
    mr.away_goals AS away_goals,
    ms.away_shots AS away_shots,
    ms.away_shots_on_target AS away_shots_on_target,
    ms.away_corners AS away_corners,
    ms.away_fouls_committed AS away_fouls_committed,
    ms.away_free_kicks_conceded AS away_free_kicks_conceded,
    ms.away_offsides AS away_offsides,
    ms.away_yellow AS away_yellow,
    ms.away_red AS away_red
FROM v_match_results AS mr
JOIN match_stats AS ms ON mr.match_id = ms.match_id;

-- Statistics of a particular team in a particular season.
CREATE VIEW v_team_stats AS
WITH team_matches AS (
    -- Team plays as local.
    SELECT 
        season_id,
        home_team_id AS team_id,
        home_team_goals AS goals_scored,
        away_team_goals AS goals_conceded
    FROM matches

    UNION ALL

    -- Team plays as visitor.
    SELECT 
        season_id,
        away_team_id AS team_id,
        away_team_goals AS goals_scored,
        home_team_goals AS goals_conceded
    FROM matches
)
SELECT
    tm.season_id AS season_id,
    t.name AS team_name,
    COUNT(*) AS matches_played,
    SUM(tm.goals_scored) AS total_goals_scored,
    SUM(tm.goals_conceded) AS total_goals_conceded
FROM team_matches AS tm
JOIN teams AS t ON tm.team_id = t.id
GROUP BY tm.season_id, tm.team_id, t.name;

