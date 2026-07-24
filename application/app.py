"""Flask application entry point."""

from flask import Flask, render_template
import pandas as pd
import joblib
from pathlib import Path
import sys
import json
import os
from data_manager import get_next_matches, get_full_team_name, get_team_abbreviation, get_team_svg
from src.models import random_forest
from src.etl.extract import load_all_seasons
from src.etl.transform import clean_matches
from src.etl.features import build_features

# Set working directory to script location
script_dir = Path(__file__).resolve().parent
os.chdir(script_dir)
sys.path.append('src')

app = Flask(__name__)

# Load trained models and data at startup
print("Loading models and data...")
try:
    # Load historical data
    seasons = ['1920', '2021', '2122', '2223', '2324', '2425', '2526']
    all_matches = pd.concat([pd.read_csv(f'data/raw/season_{s}.csv') for s in seasons])
    clean_data = clean_matches(all_matches)
    feature_data = build_features(clean_data)
    
    # Load trained Random Forest model
    rf_model, label_encoder, X_test, y_test = random_forest.train_random_forest(feature_data)
    
    # Save feature columns used during training
    from etl.features import split_features_targets
    X_train, y_train = split_features_targets(feature_data)
    training_feature_cols = X_train.columns.tolist()
    print("Models loaded successfully")
except Exception as e:
    print(f"Error loading models: {e}")
    rf_model = None
    label_encoder = None
    feature_data = None
    training_feature_cols = None


def calculate_importance_score(match, feature_data=None):
    """Calculate importance score for a match based on team quality and prediction balance.
    
    Args:
        match (dict): Match dictionary with prediction probabilities
        feature_data (DataFrame): Historical data with ELO ratings
    
    Returns:
        float: Importance score (0-1), higher = more important
    """
    if not match.get('prediction'):
        return 0.0
    
    pred = match['prediction']
    home_prob = pred.get('home_win', 0.33)
    away_prob = pred.get('away_win', 0.33)
    
    # Get ELO ratings for both teams (proxy for table position)
    home_team = match.get('home_team')
    away_team = match.get('away_team')
    
    elo_score = 0.0
    if feature_data is not None and 'elo_home_pre' in feature_data.columns:
        # Get latest ELO for home team
        home_elo = feature_data[feature_data['home_team'] == home_team]['elo_home_pre'].iloc[-1] if len(feature_data[feature_data['home_team'] == home_team]) > 0 else 1500
        # Get latest ELO for away team (as away team)
        away_elo = feature_data[feature_data['away_team'] == away_team]['elo_away_pre'].iloc[-1] if len(feature_data[feature_data['away_team'] == away_team]) > 0 else 1500
        
        # Normalize ELO (typical range: 1200-1800)
        max_elo = 1800
        min_elo = 1200
        norm_home_elo = (home_elo - min_elo) / (max_elo - min_elo)
        norm_away_elo = (away_elo - min_elo) / (max_elo - min_elo)
        
        # Higher ELO teams = more interesting
        elo_score = (norm_home_elo + norm_away_elo) / 2
    
    # Balance score (less weight now)
    balance_score = 1 - abs(home_prob - away_prob)
    
    # Combined score: prioritize team quality (ELO) over balance
    importance_score = 0.6 * elo_score + 0.4 * balance_score
    
    return importance_score


def get_featured_match(matches, feature_data=None):
    """Select the most important match from a list of matches.
    
    Args:
        matches (list): List of match dictionaries
        feature_data (DataFrame): Historical data with ELO ratings
    
    Returns:
        dict: The match with highest importance score, or None
    """
    if not matches:
        return None
    
    # Calculate importance score for each match
    for match in matches:
        match['importance_score'] = calculate_importance_score(match, feature_data)
    
    # Sort by importance score and return the highest
    featured = max(matches, key=lambda m: m['importance_score'])
    return featured


@app.route('/')
def dashboard():
    """Home page - Dashboard."""
    next_matches = get_next_matches()
    #If everything is correct we return probabilities
    if rf_model is not None and label_encoder is not None and feature_data is not None:
        for match in next_matches:
            # Convert abbreviations to full names for model prediction
            home_full = get_full_team_name(match['home_team'])
            away_full = get_full_team_name(match['away_team'])
            match['prediction'] = random_forest.predict_match_simple(
                rf_model, label_encoder, feature_data, home_full, away_full, training_feature_cols
            )
            # Add SVG filenames for display
            match['home_svg'] = get_team_svg(match['home_team'])
            match['away_svg'] = get_team_svg(match['away_team'])
    else: #for the script not to break
        for match in next_matches:
            match['prediction'] = {'home_win': 0.0, 'draw': 0.0, 'away_win': 0.0}
            match['home_svg'] = get_team_svg(match['home_team'])
            match['away_svg'] = get_team_svg(match['away_team'])

    # We get the model's accuracy from artifacts/model_comparison.json
    try:
        with open('artifacts/model_comparison.json', 'r') as f:
            model_results = json.load(f)
        rf_accuracy = model_results['random_forest']['accuracy']
    except FileNotFoundError:
        rf_accuracy = 0.0

    #We get a pipeline status
    raw_data_exists = Path('data/raw').exists() and len(list(Path('data/raw').glob('*.csv'))) > 0
    processed_data_exists = Path('data/processed').exists() and len(list(Path('data/processed').glob('*.csv'))) > 0
    pipeline_status = 'running' if raw_data_exists and processed_data_exists else 'error'
    
    # Get featured match (most important)
    featured_match = get_featured_match(next_matches, feature_data)

    return render_template('dashboard.html', next_matches=next_matches, rf_accuracy=rf_accuracy, pipeline_status=pipeline_status, featured_match=featured_match, active_page='dashboard', matchweek=12, matchweek_dates='8 - 10 Nov, 2025')



@app.route('/showdown')
def showdown():
    """Model comparison page - Random Forest vs Poisson."""
    # Load model comparison results from artifacts
    script_dir = Path(__file__).parent
    artifacts_path = script_dir / 'artifacts' / 'model_comparison.json'
    
    try:
        with open(artifacts_path, 'r') as f:
            model_results = json.load(f)
    except FileNotFoundError:
        model_results = {
            'poisson': {'accuracy': 0.0, 'predictions': 0, 'model_type': 'Poisson Distribution'},
            'random_forest': {'accuracy': 0.0, 'predictions': 0, 'model_type': 'Random Forest Classifier'},
            'test_season': 'N/A',
            'test_matches': 0
        }
    
    return render_template('showdown.html', model_results=model_results, active_page='model_showdown')


@app.route('/predictor')
def predictor():
    """Match prediction page."""
    # TODO: Get list of all teams from database
    # TODO: Load Random Forest model and feature importance
    # TODO: Load feature engineering pipeline
    # TODO: Pass teams list to template for dropdowns
    return render_template('predictor.html')


@app.route('/predictor', methods=['POST'])
def predict_match():
    """Handle match prediction form submission."""
    # TODO: Get home_team and away_team from form
    # TODO: Load historical data for both teams
    # TODO: Apply feature engineering pipeline
    # TODO: Get prediction from Random Forest model
    # TODO: Get prediction from Poisson model
    # TODO: Get feature importance from Random Forest
    # TODO: Return prediction results to template
    return render_template('predictor.html')


@app.route('/simulator')
def simulator():
    """League simulator page - Monte Carlo simulations."""
    # TODO: Get current standings from database
    # TODO: Get remaining fixtures from database
    # TODO: Load simulation parameters (number of simulations, etc.)
    # TODO: Pass data to template
    return render_template('simulator.html')


@app.route('/simulator', methods=['POST'])
def run_simulation():
    """Handle Monte Carlo simulation."""
    # TODO: Get simulation parameters from form
    # TODO: Run Monte Carlo simulation using Poisson model
    # TODO: Calculate probabilities for each team (win league, CL spots, relegation)
    # TODO: Generate projected final table
    # TODO: Return results to template
    return render_template('simulator.html')


@app.route('/architecture')
def architecture():
    """Architecture documentation page."""
    # TODO: Get pipeline status information
    # TODO: Get model metadata (training date, data used, etc.)
    # TODO: Get database schema information
    # TODO: Pass data to template
    return render_template('architecture.html')


if __name__ == "__main__":
    app.run(debug=False)
