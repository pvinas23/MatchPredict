"""Evaluate Poisson and Random Forest models and save metrics to JSON."""

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from etl.extract import load_all_seasons
from etl.transform import clean_matches
from etl.features import build_features
from models import poisson, random_forest

def evaluate_poisson(train_data, test_data):
    """Evaluate Poisson model on test data with detailed statistics."""
    print("  Fitting Poisson model...")
    train_clean = train_data[['hometeam', 'awayteam', 'fthg', 'ftag']].copy()
    train_clean.columns = ['home_team', 'away_team', 'home_goals', 'away_goals']
    model_state = poisson.fit_poisson_model(train_clean)
    
    predictions = []
    actual = []
    matchweek_stats = {}
    counter = 0
    
    for idx, row in test_data.iterrows():
        home_team = row['hometeam']
        away_team = row['awayteam']
        actual_result = row['ftr']
        matchweek = row.get('matchweek', counter // 10 + 1)
        
        try:
            probs = poisson.predict_match(home_team, away_team, model_state)
            
            if probs['home'] > probs['draw'] and probs['home'] > probs['away']:
                pred = 'H'
            elif probs['draw'] > probs['home'] and probs['draw'] > probs['away']:
                pred = 'D'
            else:
                pred = 'A'
            
            counter += 1
            predictions.append(pred)
            actual.append(actual_result)
            
            if matchweek not in matchweek_stats:
                matchweek_stats[matchweek] = {'correct': 0, 'total': 0}
            matchweek_stats[matchweek]['total'] += 1
            if pred == actual_result:
                matchweek_stats[matchweek]['correct'] += 1
                
        except:
            continue
    
    if len(predictions) == 0:
        return {'accuracy': 0.0, 'predictions': 0, 'matchweek_stats': {}, 'prediction_distribution': {}}
    
    accuracy = accuracy_score(actual, predictions)
    
    pred_dist = {'H': predictions.count('H'), 'D': predictions.count('D'), 'A': predictions.count('A')}
    actual_dist = {'H': actual.count('H'), 'D': actual.count('D'), 'A': actual.count('A')}
    
    correct_by_type = {'H': 0, 'D': 0, 'A': 0}
    total_by_type = {'H': 0, 'D': 0, 'A': 0}
    for pred, act in zip(predictions, actual):
        total_by_type[act] += 1
        if pred == act:
            correct_by_type[act] += 1
    
    accuracy_by_type = {}
    for result_type in ['H', 'D', 'A']:
        if total_by_type[result_type] > 0:
            accuracy_by_type[result_type] = round(correct_by_type[result_type] / total_by_type[result_type] * 100, 2)
        else:
            accuracy_by_type[result_type] = 0
    
    return {
        'accuracy': accuracy,
        'predictions': len(predictions),
        'matchweek_stats': matchweek_stats,
        'prediction_distribution': pred_dist,
        'actual_distribution': actual_dist,
        'accuracy_by_type': accuracy_by_type,
        'correct_predictions': sum(correct_by_type.values()),
        'total_predictions': len(predictions)
    }

def evaluate_random_forest(model, label_encoder, test_with_features, feature_cols):
    """Evaluate Random Forest model on test data with detailed statistics."""
    X_test = test_with_features[feature_cols].fillna(0)
    y_test = test_with_features['result'] if 'result' in test_with_features.columns else test_with_features['ftr']
    
    y_test_encoded = label_encoder.transform(y_test)
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test_encoded, y_pred)
    
    y_pred_labels = label_encoder.inverse_transform(y_pred)
    y_test_labels = label_encoder.inverse_transform(y_test_encoded)
    
    pred_dist = {'H': list(y_pred_labels).count('H'), 'D': list(y_pred_labels).count('D'), 'A': list(y_pred_labels).count('A')}
    actual_dist = {'H': list(y_test_labels).count('H'), 'D': list(y_test_labels).count('D'), 'A': list(y_test_labels).count('A')}
    
    correct_by_type = {'H': 0, 'D': 0, 'A': 0}
    total_by_type = {'H': 0, 'D': 0, 'A': 0}
    for pred, act in zip(y_pred_labels, y_test_labels):
        total_by_type[act] += 1
        if pred == act:
            correct_by_type[act] += 1
    
    accuracy_by_type = {}
    for result_type in ['H', 'D', 'A']:
        if total_by_type[result_type] > 0:
            accuracy_by_type[result_type] = round(correct_by_type[result_type] / total_by_type[result_type] * 100, 2)
        else:
            accuracy_by_type[result_type] = 0
    
    matchweek_stats = {}
    for idx in range(len(y_test_labels)):
        matchweek = idx // 10 + 1
        if matchweek not in matchweek_stats:
            matchweek_stats[matchweek] = {'correct': 0, 'total': 0}
        matchweek_stats[matchweek]['total'] += 1
        if y_pred_labels[idx] == y_test_labels[idx]:
            matchweek_stats[matchweek]['correct'] += 1
    
    return {
        'accuracy': accuracy,
        'predictions': len(y_test),
        'matchweek_stats': matchweek_stats,
        'prediction_distribution': pred_dist,
        'actual_distribution': actual_dist,
        'accuracy_by_type': accuracy_by_type,
        'correct_predictions': sum(correct_by_type.values()),
        'total_predictions': len(y_test)
    }

def main():
    print("Loading data...")
    seasons = ['1920', '2021', '2122', '2223', '2324', '2425', '2526']
    load_all_seasons(seasons)
    
    script_dir = Path(__file__).parent
    
    data_files = []
    for season in seasons:
        file_path = script_dir / f'data/raw/season_{season}.csv'
        
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['Season'] = season
            data_files.append(df)
            print(f"  Loaded {file_path.name}: {len(df)} matches")
        else:
            print(f"  Warning: {file_path} not found")
    
    all_data = pd.concat(data_files, ignore_index=True)
    
    available_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'Season', 
                     'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR']
    cols_to_use = [col for col in available_cols if col in all_data.columns]
    all_data = all_data[cols_to_use].copy()
    all_data.columns = all_data.columns.str.lower()
    all_data['date'] = pd.to_datetime(all_data['date'], dayfirst=True, errors='coerce')
    all_data = all_data.dropna(subset=['date', 'hometeam', 'awayteam'])
    
    train_data = all_data[all_data['season'] < '2526'].copy()
    test_data = all_data[all_data['season'] == '2526'].copy()
    
    print(f"Train data: {len(train_data)} matches")
    print(f"Test data: {len(test_data)} matches")
    
    print("Using full ETL pipeline for feature engineering...")
    
    try:
        all_clean = clean_matches(all_data)
        all_clean['season'] = all_data['season'].values
        
        train_clean = all_clean[all_clean['season'] < '2526'].copy()
        test_clean = all_clean[all_clean['season'] == '2526'].copy()
        
        feature_data = build_features(all_clean)
        
        train_with_features = feature_data[feature_data['season'] < '2526'].copy()
        test_with_features = feature_data[feature_data['season'] == '2526'].copy()
        
        exclude_cols = ['match_datetime', 'home_team', 'away_team', 'result', 'home_goals', 'away_goals', 'season']
        feature_cols = [col for col in train_with_features.columns if col not in exclude_cols and train_with_features[col].dtype in ['int64', 'float64']]
        
        print(f"Using {len(feature_cols)} features from full pipeline")
        
    except Exception as e:
        print(f"Error using full pipeline: {e}")
        print("Falling back to simple features...")
        
        def create_simple_features(df):
            df = df.copy()
            df = df.sort_values('date')
            
            team_stats = {}
            for team in df['hometeam'].unique():
                home_matches = df[df['hometeam'] == team]
                away_matches = df[df['awayteam'] == team]
                
                home_goals_scored = home_matches['fthg'].mean() if len(home_matches) > 0 else 1.0
                home_goals_conceded = home_matches['ftag'].mean() if len(home_matches) > 0 else 1.0
                away_goals_scored = away_matches['ftag'].mean() if len(away_matches) > 0 else 1.0
                away_goals_conceded = away_matches['fthg'].mean() if len(away_matches) > 0 else 1.0
                
                team_stats[team] = {
                    'avg_goals_scored': (home_goals_scored + away_goals_scored) / 2,
                    'avg_goals_conceded': (home_goals_conceded + away_goals_conceded) / 2
                }
            
            df['home_avg_goals_scored'] = df['hometeam'].map(lambda x: team_stats.get(x, {}).get('avg_goals_scored', 1.0))
            df['home_avg_goals_conceded'] = df['hometeam'].map(lambda x: team_stats.get(x, {}).get('avg_goals_conceded', 1.0))
            df['away_avg_goals_scored'] = df['awayteam'].map(lambda x: team_stats.get(x, {}).get('avg_goals_scored', 1.0))
            df['away_avg_goals_conceded'] = df['awayteam'].map(lambda x: team_stats.get(x, {}).get('avg_goals_conceded', 1.0))
            
            return df
        
        train_with_features = create_simple_features(train_data)
        test_with_features = create_simple_features(test_data)
        feature_cols = ['home_avg_goals_scored', 'home_avg_goals_conceded', 
                        'away_avg_goals_scored', 'away_avg_goals_conceded']
    
    print("Training Random Forest with optimized hyperparameters...")
    X_train = train_with_features[feature_cols].fillna(0)
    y_train = train_with_features['result'] if 'result' in train_with_features.columns else train_with_features['ftr']
    
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train_encoded)
    
    rf_train_pred = rf_model.predict(X_train)
    rf_accuracy = accuracy_score(y_train_encoded, rf_train_pred)
    
    print("Evaluating Poisson...")
    poisson_metrics = evaluate_poisson(train_data, test_data)
    
    print("Evaluating Random Forest...")
    rf_metrics = evaluate_random_forest(rf_model, label_encoder, test_with_features, feature_cols)
    
    print("Calculating additional metrics...")
    
    results = {
        'poisson': {
            'accuracy': round(poisson_metrics['accuracy'] * 100, 2),
            'predictions': poisson_metrics['predictions'],
            'model_type': 'Poisson Distribution',
            'correct_predictions': poisson_metrics['correct_predictions'],
            'total_predictions': poisson_metrics['total_predictions'],
            'prediction_distribution': poisson_metrics['prediction_distribution'],
            'actual_distribution': poisson_metrics['actual_distribution'],
            'accuracy_by_type': poisson_metrics['accuracy_by_type'],
            'matchweek_stats': poisson_metrics['matchweek_stats']
        },
        'random_forest': {
            'accuracy': round(rf_metrics['accuracy'] * 100, 2),
            'predictions': rf_metrics['predictions'],
            'model_type': 'Random Forest Classifier',
            'correct_predictions': rf_metrics['correct_predictions'],
            'total_predictions': rf_metrics['total_predictions'],
            'prediction_distribution': rf_metrics['prediction_distribution'],
            'actual_distribution': rf_metrics['actual_distribution'],
            'accuracy_by_type': rf_metrics['accuracy_by_type'],
            'matchweek_stats': rf_metrics['matchweek_stats']
        },
        'test_season': '25/26',
        'test_matches': len(test_data)
    }
    
    script_dir = Path(__file__).parent
    artifacts_dir = script_dir / 'artifacts'
    artifacts_dir.mkdir(exist_ok=True)
    
    with open(artifacts_dir / 'model_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to artifacts/model_comparison.json")
    print(f"Poisson Accuracy: {results['poisson']['accuracy']}%")
    print(f"Random Forest Accuracy: {results['random_forest']['accuracy']}%")
    
    import joblib
    joblib.dump(rf_model, artifacts_dir / 'rf_model.pkl')
    joblib.dump(label_encoder, artifacts_dir / 'label_encoder.pkl')
    joblib.dump(feature_cols, artifacts_dir / 'feature_cols.pkl')
    
    print("Models saved to artifacts/")

if __name__ == '__main__':
    main()
