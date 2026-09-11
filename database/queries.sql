-- Query 1: league table with points, goal difference and ranking at a specific
-- date.

WITH points AS (
    SELECT
        season_id,
        date,
        home_team_id AS team_id,
        home_team_goals - away_team_goals AS goal_diff,
        CASE
            WHEN result = 'H' THEN 3
            WHEN result = 'D' THEN 1
            ELSE 0
        END AS points
    FROM matches

    UNION ALL

    SELECT
        season_id,
        date,
        away_team_id AS team_id,
        away_team_goals - home_team_goals AS goal_diff,
        CASE
            WHEN result = 'A' THEN 3
            WHEN result = 'D' THEN 1
            ELSE 0
        END AS points
    FROM matches
)
SELECT
    t.name AS team,
    s.name AS season_name,
    SUM(p.points) AS total_points,
    SUM(p.goal_diff) AS goals_difference,
    ROW_NUMBER() OVER (
        ORDER BY SUM(p.points) DESC, SUM(p.goal_diff) DESC, t.name ASC
    ) AS position
FROM points AS p
JOIN teams AS t ON p.team_id = t.id
JOIN seasons AS s ON s.id = p.season_id
WHERE p.date <= :target_date
  AND s.name = :season_name
GROUP BY t.name, s.name
ORDER BY total_points DESC, goals_difference DESC, team ASC;


-- Query 2: head-to-head query for two teams with historical results.

WITH matchup AS (
    SELECT
        m.*,    --All the columns from matches
        th.name AS home_team_name,
        ta.name AS away_team_name
    FROM matches AS m
    JOIN teams AS th ON m.home_team_id = th.id
    JOIN teams AS ta ON m.away_team_id = ta.id
    WHERE (
        (th.name = :team_a_name AND ta.name = :team_b_name)
        OR
        (th.name = :team_b_name AND ta.name = :team_a_name)
    )
)
SELECT
    COUNT(*) AS total_matches,
    SUM(CASE
        WHEN home_team_name = :team_a_name AND result = 'H' THEN 1
        WHEN away_team_name = :team_a_name AND result = 'A' THEN 1
        ELSE 0
    END) AS team_a_wins,
    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) AS draws,
    SUM(CASE
        WHEN home_team_name = :team_b_name AND result = 'H' THEN 1
        WHEN away_team_name = :team_b_name AND result = 'A' THEN 1
        ELSE 0
    END) AS team_b_wins,
    SUM(CASE WHEN home_team_name = :team_a_name THEN home_team_goals ELSE away_team_goals END) AS team_a_goals,
    SUM(CASE WHEN home_team_name = :team_b_name THEN home_team_goals ELSE away_team_goals END) AS team_b_goals
FROM matchup;


-- Query 3: points obtained by a particular team in the last five matches prior
-- to a given date.

WITH team_matches AS (
    SELECT
        date,
        CASE
            WHEN home_team_id = :target_team_id AND result = 'H' THEN 3
            WHEN away_team_id = :target_team_id AND result = 'A' THEN 3
            WHEN result = 'D' THEN 1
            ELSE 0
        END AS points_for_match
    FROM matches
    WHERE (home_team_id = :target_team_id OR away_team_id = :target_team_id)
      AND date < :target_date
)
SELECT
    date,
    points_for_match,
    SUM(points_for_match) OVER (
        ORDER BY date
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) AS points_last_5_matches
FROM team_matches
ORDER BY date DESC
LIMIT 1;


-- Query 4: season-level summary for one team.

SELECT
    s.name AS season_name,
    t.name AS team_name,
    COUNT(*) AS matches_played,
    SUM(CASE
        WHEN m.home_team_id = t.id AND m.result = 'H' THEN 1
        WHEN m.away_team_id = t.id AND m.result = 'A' THEN 1
        ELSE 0
    END) AS wins,
    SUM(CASE WHEN m.result = 'D' THEN 1 ELSE 0 END) AS draws,
    SUM(CASE
        WHEN m.home_team_id = t.id AND m.result = 'A' THEN 1
        WHEN m.away_team_id = t.id AND m.result = 'H' THEN 1
        ELSE 0
    END) AS losses,
    SUM(CASE WHEN m.home_team_id = t.id THEN m.home_team_goals ELSE m.away_team_goals END) AS goals_for,
    SUM(CASE WHEN m.home_team_id = t.id THEN m.away_team_goals ELSE m.home_team_goals END) AS goals_against
FROM matches AS m
JOIN teams AS t ON m.home_team_id = t.id OR m.away_team_id = t.id
JOIN seasons AS s ON m.season_id = s.id
WHERE t.id = :team_id
  AND s.name = :season_name
GROUP BY s.name, t.name;


-- Query 5: model accuracy over stored predictions.

WITH evaluations AS (
    SELECT
        ps.model_name,
        ps.match_id,
        m.result AS actual_result,
        m.home_team_goals AS actual_home_goals,
        m.away_team_goals AS actual_away_goals,
        CASE
            WHEN ps.prob_home_win >= ps.prob_draw
             AND ps.prob_home_win >= ps.prob_away_win AND m.result = 'H' THEN 1
            WHEN ps.prob_draw >= ps.prob_home_win
             AND ps.prob_draw >= ps.prob_away_win AND m.result = 'D' THEN 1
            WHEN ps.prob_away_win >= ps.prob_home_win
             AND ps.prob_away_win >= ps.prob_draw AND m.result = 'A' THEN 1
            ELSE 0
        END AS correct_result,
        CASE
            WHEN pts.rank_order = 1
             AND pts.home_goals = m.home_team_goals
             AND pts.away_goals = m.away_team_goals THEN 1
            ELSE 0
        END AS correct_top_score
    FROM predictions_summary AS ps
    JOIN matches AS m ON m.id = ps.match_id
    LEFT JOIN predicted_top_scores AS pts -- Left join to include matches in which the total score wasn't predicted
        ON pts.match_id = ps.match_id
       AND pts.model_name = ps.model_name
       AND pts.rank_order = 1
)
SELECT
    model_name,
    COUNT(*) AS total_matches,
    ROUND(100 * AVG(correct_result), 2) AS result_accuracy_pct,
    ROUND(100 * AVG(correct_top_score), 2) AS top_score_accuracy_pct
FROM evaluations
GROUP BY model_name
ORDER BY result_accuracy_pct DESC, top_score_accuracy_pct DESC;


-- Query 6: compare the model against the betting market.
--
-- Why this query matters:
-- This is the best way to use betting odds in the project without turning the
-- model into a copy of the market. The odds remain a benchmark: they tell you
-- how difficult the prediction task is and whether your model adds value beyond
-- what bookmakers already implied.
--
-- Why I would keep it:
-- If you include bookmaker odds in the training dataframe, the model can become
-- very strong, but the evaluation story gets less interesting. By keeping them
-- here instead, you can say: "the model is compared against the market, not
-- trained to imitate it".
WITH market_predictions AS (
    SELECT
        mo.match_id,
        m.result AS actual_result,
        CASE
            WHEN mo.b365_home_win_odds IS NOT NULL
             AND mo.b365_draw_odds IS NOT NULL
             AND mo.b365_away_win_odds IS NOT NULL
            THEN CASE
                WHEN (1 / mo.b365_home_win_odds) >= (1 / mo.b365_draw_odds)
                 AND (1 / mo.b365_home_win_odds) >= (1 / mo.b365_away_win_odds) THEN 'H'
                WHEN (1 / mo.b365_draw_odds) >= (1 / mo.b365_home_win_odds)
                 AND (1 / mo.b365_draw_odds) >= (1 / mo.b365_away_win_odds) THEN 'D'
                ELSE 'A'
            END
            ELSE NULL
        END AS market_predicted_result
    FROM match_market_odds AS mo
    JOIN matches AS m ON m.id = mo.match_id
)
SELECT
    COUNT(*) AS total_matches_with_market_data,
    SUM(CASE WHEN market_predicted_result = actual_result THEN 1 ELSE 0 END) AS market_correct_predictions,
    ROUND(100 * AVG(CASE WHEN market_predicted_result = actual_result THEN 1 ELSE 0 END), 2) AS market_accuracy_pct
FROM market_predictions
WHERE market_predicted_result IS NOT NULL;

