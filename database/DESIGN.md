# Design Document

By Pablo Viñas Lozano

Video overview: <URL HERE>

## Scope

In this section you should answer the following questions:

* What is the purpose of your database? This database is designed to store and analyze football match data from the Premier League, including team information, match results, match statistics, and model predictions. The information is stored to train machine learning models to predict match outcomes and evaluate their accuracy.

* Which people, places, things, etc. are you including in the scope of your database? The scope includes football teams, leagues, seasons, matches, and match statistics.

* Which people, places, things, etc. are *outside* the scope of your database? The scope does not include user accounts or authentication.

## Functional Requirements

In this section you should answer the following questions:

* What should a user be able to do with your database? A user should be able to query the database to get information about football matches, teams, and players.
* What's beyond the scope of what a user should be able to do with your database? Creating user accounts is outside the things that can be done with the database.

## Representation
![Match_predict_diagram](er_diagram.png)

### Entities

In this section you should answer the following questions:

* Which entities will you choose to represent in your database? The entities are teams, leagues, seasons, matches, match statistics, team ratings, market odds, and model predictions.

* What attributes will those entities have?
teams: id, name
leagues: id, name, country, tier
seasons: id, league_id, name
matches: id, season_id, date, home_team_id, away_team_id, home_team_goals, away_team_goals, result, referee
match_stats: match_id, home_shots, away_shots, home_shots_on_target, away_shots_on_target, home_corners, away_corners, home_yellow, away_yellow, home_red, away_red
team_ratings: id, team_id, season_id, date, rating
match_market_odds: match_id, b365_home_win_odds, b365_draw_odds, b365_away_win_odds, market_avg_home_win_odds, market_avg_draw_odds, market_avg_away_win_odds
predictions_summary: id, match_id, model_name, prob_home_win, prob_draw, prob_away_win
predicted_top_scores: rank_order, model_name, match_id, home_goals, away_goals, probability

* Why did you choose the types you did? I chose varchar for names and country because they are text values. I chose int for ids and goals because they are whole numbers. I chose datetime for date because it is a date and time value. I chose varchar for result because it is a single character value, 'H' for home team win, 'A' for away team win, and 'D' for draw. I chose DECIMAL for ratings and odds to handle decimal precision accurately.


* Why did you choose the constraints you did? I chose unique for name because it is a unique value. I chose check for goals because it must be a non-negative value. I chose check for result because it must be one of three values.

### Relationships

In this section you should include your entity relationship diagram and describe the relationships between the entities in your database.
The diagram is ./diagrams/er_diagram.png

The relationships between entities are:

- **leagues → seasons (1:N)**: One league has multiple seasons. This allows the database to scale to multiple leagues if needed, even though the current implementation focuses on the Premier League.

- **seasons → matches (1:N)**: One season contains multiple matches. The foreign key constraint ensures that every match belongs to a valid season.

- **teams → matches (1:N)**: One team participates in multiple matches as either home or away. Each match references two teams (home_team_id and away_team_id), with a check constraint ensuring a team cannot play against itself.

- **matches → match_stats (1:1)**: Each match has exactly one set of statistics. The match_id is both the primary key of match_stats and a foreign key to matches, with CASCADE delete to maintain consistency when a match is removed.

- **matches → match_market_odds (1:1)**: Each match has at most one set of betting odds. This keeps market data separate from match results to avoid data leakage in model training.

- **matches → predictions_summary (1:N)**: One match can have predictions from multiple models (e.g., Poisson, Random Forest). This allows comparing different models on the same match.

- **matches → predicted_top_scores (1:N)**: One match can have multiple predicted scorelines with different probabilities, ranked by likelihood.

- **teams → team_ratings (1:N)**: One team has multiple rating values over time, one per match date. This tracks team strength evolution throughout a season.

## Optimizations

In this section you should answer the following questions: 

* Which optimizations (e.g., indexes, views) did you create? Why?

**Indexes:**
- `idx_matches_date` on matches(date): Accelerates time-based queries like "all matches before a specific date" used in league table calculations.
- `idx_team_ratings_date` on team_ratings(date): Speeds up queries that retrieve a team's rating history.
- `idx_team_ratings_season` on team_ratings(season_id): Optimizes filtering by season when analyzing team performance within a specific period.
- `idx_matches_head_to_head_home_away` on matches(home_team_id, away_team_id): Enables efficient head-to-head queries between two specific teams.
- `idx_matches_head_to_head_away_home` on matches(away_team_id, home_team_id): Mirrors the previous index for queries where the team order is reversed.
- `idx_matches_season` on matches(season_id): Accelerates season-based filtering.
- `idx_matches_home_team` and `idx_matches_away_team`: Speed up queries that filter matches by a specific team.

**Views:**
- `v_match_results`: Joins matches with seasons and teams to provide a human-readable view of match results with team names instead of IDs.
- `v_match_analytics`: Combines match results with detailed statistics from match_stats, providing a comprehensive view for analysis.
- `v_team_stats`: Uses a CTE with UNION ALL to aggregate team performance (goals scored/conceded) across home and away matches, calculating season-level statistics.

These optimizations reduce query complexity for end users and improve performance for common analytical patterns.

## Limitations

In this section you should answer the following questions:

* What are the limitations of your design? The limitations of my design are:
  - It is optimized for a single league (Premier League) rather than multi-league scalability
  - It does not include player-level data (individual player statistics, injuries, transfers)
  - It is not optimized for real-time data processing or live match updates
  - It does not include user authentication or personalization features
  - The model evaluation assumes historical data is representative of future performance (standard ML limitation)

* What might your database not be able to represent very well? My database might not be able to represent very well:
  - The impact of individual player injuries, suspensions, or transfers on team performance
  - Managerial changes and their effect on team tactics and results
  - External factors like weather conditions, travel fatigue, or crowd influence
  - Complex tactical formations or playing styles that evolve over time
  - Correlation between different leagues or international competitions