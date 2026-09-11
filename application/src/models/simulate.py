"""Monte Carlo season simulation on top of the Poisson goal model.

Samples goal counts for every remaining fixture, accumulates points and
goal difference per simulated season, and aggregates finishing positions
into title / top-4 / relegation probabilities.
"""

import numpy as np

from . import poisson

TOP_POSITIONS = 4       # Champions League spots
RELEGATION_SPOTS = 3


def simulate_season(fixtures, model_state, n_simulations=1000, random_state=42):
    """Simulate a season from a list of fixtures.

    Args:
        fixtures: iterable of (home_team, away_team) pairs.
        model_state: fitted Poisson model from poisson.fit_poisson_model.
        n_simulations: number of full-season simulations.

    Returns:
        List of per-team dicts sorted by expected points, each with expected
        points, expected goal difference, and title/top-4/relegation odds.
    """
    fixtures = list(fixtures)
    teams = sorted({team for fixture in fixtures for team in fixture})
    team_index = {team: i for i, team in enumerate(teams)}
    n_teams = len(teams)

    home_idx = np.array([team_index[home] for home, _ in fixtures])
    away_idx = np.array([team_index[away] for _, away in fixtures])
    lambdas = np.array([poisson.expected_goals(home, away, model_state)
                        for home, away in fixtures])

    rng = np.random.default_rng(random_state)
    home_goals = rng.poisson(lambdas[:, 0], size=(n_simulations, len(fixtures)))
    away_goals = rng.poisson(lambdas[:, 1], size=(n_simulations, len(fixtures)))

    home_points = np.where(home_goals > away_goals, 3, np.where(home_goals == away_goals, 1, 0))
    away_points = np.where(away_goals > home_goals, 3, np.where(home_goals == away_goals, 1, 0))

    points = np.zeros((n_simulations, n_teams))
    goal_diff = np.zeros((n_simulations, n_teams))
    for fixture, (h, a) in enumerate(zip(home_idx, away_idx)):
        points[:, h] += home_points[:, fixture]
        points[:, a] += away_points[:, fixture]
        margin = home_goals[:, fixture] - away_goals[:, fixture]
        goal_diff[:, h] += margin
        goal_diff[:, a] -= margin

    # Rank by points with goal difference as tiebreaker (scaled to never
    # outweigh a whole point).
    ranking_score = points + goal_diff / 1000.0
    # Position 1 = best score in the simulation.
    positions = (-ranking_score).argsort(axis=1).argsort(axis=1) + 1

    table = []
    for team, i in team_index.items():
        table.append({
            "team": team,
            "expected_points": float(points[:, i].mean()),
            "expected_goal_diff": float(goal_diff[:, i].mean()),
            "title_pct": float((positions[:, i] == 1).mean() * 100),
            "top4_pct": float((positions[:, i] <= TOP_POSITIONS).mean() * 100),
            "relegation_pct": float(
                (positions[:, i] > n_teams - RELEGATION_SPOTS).mean() * 100
            ),
        })

    table.sort(key=lambda row: row["expected_points"], reverse=True)
    return table
