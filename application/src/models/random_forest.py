"""Random Forest classifier for match prediction.

Uses sklearn RandomForestClassifier with engineered features.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
try:
    from ..etl.features import split_features_targets
except ImportError:
    from etl.features import split_features_targets


def train_random_forest(feature_frame, random_state=42):
    """Train a Random Forest classifier on engineered features.

    Args:
        feature_frame (DataFrame): Features + target column
        random_state (int): Random seed for reproducibility

    Returns:
        model (RandomForestClassifier): Trained sklearn model
        label_encoder (LabelEncoder): Fitted label encoder for predictions
    """
    if "season" in feature_frame.columns:
        train = feature_frame[feature_frame['season'] != '2526']
        test = feature_frame[feature_frame['season'] == '2526']
    elif "match_datetime" in feature_frame.columns:
        train = feature_frame[feature_frame['match_datetime'] < '2025-08-01 00:00:00']
        test = feature_frame[feature_frame['match_datetime'] >= '2025-08-01 00:00:00']
    else:
        train, test = train_test_split(feature_frame, test_size=0.2, random_state=random_state)
    
    X_train, y_train = split_features_targets(train)
    X_test, y_test = split_features_targets(test)
    
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=None, min_samples_split=2, class_weight='balanced', random_state=random_state)
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    
    rf_model.fit(X_train, y_train_encoded)
    
    return rf_model, label_encoder, X_test, y_test


def evaluate_random_forest(model, label_encoder, x_test, y_test):
    """Evaluate the Random Forest on held-out data.

    Args:
        model (RandomForestClassifier): Trained model
        label_encoder (LabelEncoder): Fitted label encoder
        x_test (DataFrame): Test features
        y_test (Series): Test labels

    Returns:
        metrics (dict): {'accuracy': float}
    """
    y_test_encoded = label_encoder.transform(y_test)
    y_pred = model.predict(x_test)
    test_accuracy = accuracy_score(y_test_encoded, y_pred)
    
    y_proba = model.predict_proba(x_test)
    
    metrics = {'accuracy': test_accuracy}
    return metrics


def predict_outcome(model, label_encoder, feature_row):
    """Predict the most likely match outcome for a single feature row.

    Args:
        model (RandomForestClassifier): Trained model
        label_encoder (LabelEncoder): Fitted label encoder
        feature_row (Series or array): Single match features

    Returns:
        result (dict): {'prediction': str, 'probabilities': dict}
    """
    if len(feature_row.shape) == 1:
        feature_row = feature_row.values.reshape(1, -1)
    
    prediction = model.predict(feature_row)[0]
    prediction_label = label_encoder.inverse_transform([prediction])[0]
    probabilities = model.predict_proba(feature_row)[0]
    
    result = {
        'prediction': prediction_label,
        'probabilities': {
            'home': probabilities[0],
            'draw': probabilities[1],
            'away': probabilities[2]
        }
    }
    return result


def predict_match_simple(model, label_encoder, historical_data, home_team, away_team, feature_cols=None):
    """Predict match probabilities for given teams using historical data.

    Args:
        model (RandomForestClassifier): Trained model
        label_encoder (LabelEncoder): Fitted label encoder
        historical_data (DataFrame): Full historical data with all matches
        home_team (str): Name of home team
        away_team (str): Name of away team
        feature_cols (list): List of feature columns used during training

    Returns:
        result (dict): {'home_win': float, 'draw': float, 'away_win': float}
    """
    from etl.features import build_features
    import numpy as np
    
    home_team_matches = historical_data[
        (historical_data['home_team'] == home_team) |
        (historical_data['away_team'] == home_team)
    ]
    
    away_team_matches = historical_data[
        (historical_data['home_team'] == away_team) |
        (historical_data['away_team'] == away_team)
    ]
    
    if len(home_team_matches) < 5 and len(away_team_matches) < 5:
        return {'home_win': 0.45, 'draw': 0.25, 'away_win': 0.30}
    
    if len(home_team_matches) < 5:
        return {'home_win': 0.20, 'draw': 0.25, 'away_win': 0.55}
    
    if len(away_team_matches) < 5:
        return {'home_win': 0.65, 'draw': 0.25, 'away_win': 0.10}
    
    team_matches = historical_data[
        (historical_data['home_team'] == home_team) |
        (historical_data['away_team'] == home_team) |
        (historical_data['home_team'] == away_team) |
        (historical_data['away_team'] == away_team)
    ]
    
    if len(team_matches) < 10:
        return {'home_win': 0.45, 'draw': 0.25, 'away_win': 0.30}
    
    features_df = build_features(team_matches)
    
    home_matches = features_df[features_df['home_team'] == home_team]
    away_matches = features_df[features_df['away_team'] == away_team]
    
    if len(home_matches) == 0 or len(away_matches) == 0:
        if len(home_team_matches) >= 5 and len(away_team_matches) < 5:
            return {'home_win': 0.65, 'draw': 0.25, 'away_win': 0.10}
        elif len(away_team_matches) >= 5 and len(home_team_matches) < 5:
            return {'home_win': 0.20, 'draw': 0.25, 'away_win': 0.55}
        else:
            return {'home_win': 0.45, 'draw': 0.25, 'away_win': 0.30}
    
    home_features = home_matches.iloc[-1]
    away_features = away_matches.iloc[-1]
    
    if feature_cols is None:
        feature_cols = [col for col in features_df.columns 
                       if col not in ['match_datetime', 'home_team', 'away_team', 'result',
                                   'home_goals', 'away_goals', 'season']
                       and features_df[col].dtype in ['int64', 'float64']]
    
    feature_row = pd.Series(0.0, index=feature_cols)
    
    for col in feature_cols:
        if col in home_features.index and col in away_features.index:
            if col.endswith('_home'):
                feature_row[col] = home_features[col]
            elif col.endswith('_away'):
                feature_row[col] = away_features[col]
            else:
                feature_row[col] = (home_features[col] + away_features[col]) / 2
        elif col in home_features.index:
            feature_row[col] = home_features[col]
        elif col in away_features.index:
            feature_row[col] = away_features[col]
    
    feature_row = feature_row.fillna(0)
    
    result = predict_outcome(model, label_encoder, feature_row)
    
    return {
        'home_win': result['probabilities']['home'],
        'draw': result['probabilities']['draw'],
        'away_win': result['probabilities']['away']
    }
