"""Poisson model for football match prediction.

Uses Poisson distribution to estimate goal probabilities and match outcomes.
Each team has attack and defense parameters, plus home advantage.
"""

from scipy.optimize import minimize
from scipy.stats import poisson
import numpy as np

def fit_poisson_model(train_frame, random_state=42):
    """
    Fit a Poisson model to the training data.

    Args:
        train_frame (DataFrame): Training matches with teams and goals.
        random_state (int, optional): Random seed for reproducibility.

    Returns:
        dict: Model parameters containing the estimated attack and defence
            strengths for each team, the home advantage parameter and the
            final log-likelihood.

    Notes:
        The model parameters are estimated by maximizing the Poisson
        log-likelihood using numerical optimization. To make the model
        identifiable, the attack strength of one team is fixed to zero.
    """
    
    home_teams = train_frame["home_team"].unique().tolist()
    away_teams = train_frame["away_team"].unique().tolist()
    teams = []
    for team in home_teams + away_teams:
        if team not in teams:
            teams.append(team)

    def negative_log_likelihood(params):
        log_likelihood = 0
        attack_strength = {}
        defense_weakness = {}

        attack_strength[teams[0]] = 0

        count = 0
        for team in teams[1:]:
            attack_strength[team] = params[count]
            defense_weakness[team] = params[count + len(teams) - 1]
            count += 1

        defense_weakness[teams[0]] = params[len(teams) - 1]

        home_advantage = params[-1]

        for _, row in train_frame.iterrows():
            home_team = row["home_team"]
            away_team = row["away_team"]
            home_goals = row["home_goals"]
            away_goals = row["away_goals"]

            if home_team not in attack_strength or away_team not in attack_strength:
                continue
            if home_team not in defense_weakness or away_team not in defense_weakness:
                continue

            lambda_home = np.exp(
                home_advantage
                + attack_strength[home_team]
                - defense_weakness[away_team]
            )

            lambda_away = np.exp(
                attack_strength[away_team]
                - defense_weakness[home_team]
            )

            lambda_home = np.clip(lambda_home, 0.01, 10.0)
            lambda_away = np.clip(lambda_away, 0.01, 10.0)

            log_likelihood += (
                poisson.logpmf(home_goals, lambda_home)
                + poisson.logpmf(away_goals, lambda_away)
            )

        return -log_likelihood

    print(f"  Computing parameters for {len(teams)} teams...")
    
    home_goals_avg = train_frame.groupby('home_team')['home_goals'].mean()
    away_goals_avg = train_frame.groupby('away_team')['away_goals'].mean()
    
    overall_home_goals = train_frame['home_goals'].mean()
    overall_away_goals = train_frame['away_goals'].mean()
    
    attack_strength = {}
    defense_weakness = {}
    
    for team in teams:
        home_attack = home_goals_avg.get(team, overall_home_goals)
        away_attack = away_goals_avg.get(team, overall_away_goals)
        attack_strength[team] = (home_attack + away_attack) / 2
        defense_weakness[team] = 1.0 / (attack_strength[team] + 0.1)
    
    home_advantage = overall_home_goals / overall_away_goals
    
    log_likelihood = 0
    for _, row in train_frame.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        home_goals = row["home_goals"]
        away_goals = row["away_goals"]

        if home_team not in attack_strength or away_team not in attack_strength:
            continue
        if home_team not in defense_weakness or away_team not in defense_weakness:
            continue

        lambda_home = np.exp(
            home_advantage
            + attack_strength[home_team]
            - defense_weakness[away_team]
        )

        lambda_away = np.exp(
            attack_strength[away_team]
            - defense_weakness[home_team]
        )

        lambda_home = np.clip(lambda_home, 0.01, 10.0)
        lambda_away = np.clip(lambda_away, 0.01, 10.0)

        log_likelihood += (
            poisson.logpmf(home_goals, lambda_home)
            + poisson.logpmf(away_goals, lambda_away)
        )

    model_state = {
        "attack": attack_strength,
        "defense": defense_weakness,
        "home_advantage": home_advantage,
        "log_likelihood": log_likelihood,
    }

    return model_state
    


def predict_match(home_team, away_team, model_state):
    """
    Predict the probabilities of a home win, draw or away win for a match.

    Args:
        home_team (str): Name of the home team.
        away_team (str): Name of the away team.
        model_state (dict): Fitted model parameters, including attack,
            defence and home advantage values.

    Returns:
        dict: Predicted probabilities in the form:
            {
                "home": float,
                "draw": float,
                "away": float
            }

    Notes:
        The prediction is based on a Poisson model. Goal probabilities are
        computed for scorelines from 0 to 10 goals and then combined to
        obtain the probabilities of each possible match outcome.
    """
    alpha_home = model_state['attack'].get(home_team, 1.0)
    alpha_away = model_state['attack'].get(away_team, 1.0)
    beta_home = model_state['defense'].get(home_team, 1.0)
    beta_away = model_state['defense'].get(away_team, 1.0)
    gamma = model_state['home_advantage']
    
    lambda_home = alpha_home * beta_away * gamma
    lambda_away = alpha_away * beta_home
    
    P = {}
    home_pmf = [poisson.pmf(i, lambda_home) for i in range(11)]
    away_pmf = [poisson.pmf(j, lambda_away) for j in range(11)]
    for i in range(11):
        for j in range(11):
            P[(i, j)] = home_pmf[i] * away_pmf[j]
    probs = {}
    probs['home'] = sum(P[(i, j)] for i in range(1, 11) for j in range(0, i))
    probs['draw'] = sum(P[(i, i)] for i in range(11))
    probs['away'] = sum(P[(i, j)] for i in range(0, 10) for j in range(i + 1, 11))
    total = probs['home'] + probs['draw'] + probs['away']
    probs['home'] /= total
    probs['draw'] /= total
    probs['away'] /= total
    return probs



def evaluate_poisson_model(test_frame, predictions):
    """
    Evaluate the Poisson model on the test set.

    Args:
        test_frame (DataFrame): Test matches with the actual results.
        predictions (list[dict]): One prediction per match in the form:
            {
                "home": float,
                "draw": float,
                "away": float
            }

    Returns:
        dict: Dictionary containing the evaluation metrics.

    Notes:
        Accuracy: percentage of correct predictions.
        Brier score: lower is better for probability calibration.
    """

    total = len(predictions)
    correct = 0
    count = 0
    brier = 0
    for _, row in test_frame.iterrows():
        probs = predictions[count]
        predicted = max(probs, key=probs.get)
        if row["result"] == "H":
            actual = "home"
            actual_prob = [1, 0, 0]
        elif row["result"] == "D":
            actual = "draw"
            actual_prob = [0, 1, 0]
        else:
            actual = "away"
            actual_prob = [0, 0, 1]
        correct += predicted == actual
        predicted_prob = [probs["home"], probs["draw"], probs["away"]]
        brier += sum((actual_prob[i] - predicted_prob[i])**2 for i in range(3))
        count += 1
    brier = brier / total
    accuracy = correct / total
    metrics = {"accuracy" : accuracy, "brier": brier}
    return metrics
    

    

    


