"""Compare Poisson and Random Forest models."""

import pandas as pd
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, 'src'))

import config

from etl.extract import download_season, load_all_seasons
from etl.transform import clean_matches
from etl.features import build_features, split_features_targets
from models.poisson import fit_poisson_model, evaluate_poisson_model, predict_match
from models.random_forest import train_random_forest, evaluate_random_forest


def main():
    print("MATCH PREDICT - MODEL COMPARISON TEST")
    
    print("\n[1/5] Extracting data from football-data.co.uk...")
    seasons = ['1920', '2021', '2122', '2223', '2324', '2425', '2526']
    
    all_seasons_exist = all((config.RAW_DATA_DIR / f"season_{season}.csv").exists() for season in seasons)
    
    if all_seasons_exist:
        print(f"All {len(seasons)} seasons already exist in {config.RAW_DATA_DIR}")
    else:
        print(f"Downloading seasons: {seasons}")
        import shutil
        if config.RAW_DATA_DIR.exists():
            shutil.rmtree(config.RAW_DATA_DIR)
            config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        load_all_seasons(seasons)
        print("Download complete")
    
    print("\n[2/5] Transforming and cleaning data...")
    try:
        all_matches = pd.DataFrame()
        for season in seasons:
            file_path = config.RAW_DATA_DIR / f"season_{season}.csv"
            if file_path.exists():
                season_data = pd.read_csv(file_path)
                season_data['season'] = season  # Add season column
                all_matches = pd.concat([all_matches, season_data], ignore_index=True)
        
        if len(all_matches) > 0:
            print(f"Loaded {len(all_matches)} matches from raw data")
            clean_data = clean_matches(all_matches)
            print(f"Cleaned data: {len(clean_data)} matches")
        else:
            raise FileNotFoundError("No raw data found")
            
    except Exception as e:
        print(f"Error loading real data: {e}")
        print("Using synthetic data for testing...")
        import numpy as np
        np.random.seed(42)
        n_samples = 2000
        clean_data = pd.DataFrame({
            'match_datetime': pd.date_range('2023-08-01', periods=n_samples, freq='D'),
            'home_team': np.random.choice(['Arsenal', 'Chelsea', 'Liverpool', 'ManCity', 'ManUtd'], n_samples),
            'away_team': np.random.choice(['Arsenal', 'Chelsea', 'Liverpool', 'ManCity', 'ManUtd'], n_samples),
            'home_goals': np.random.poisson(1.5, n_samples),
            'away_goals': np.random.poisson(1.2, n_samples),
            'result': np.random.choice(['H', 'D', 'A'], n_samples, p=[0.45, 0.25, 0.3]),
            'season': np.random.choice(['2023/2024', '2025/2026'], n_samples),
            # Add columns required by features.py
            'home_shots': np.random.poisson(15, n_samples),
            'home_shots_on_target': np.random.poisson(5, n_samples),
            'home_corners': np.random.poisson(6, n_samples),
            'home_fouls_committed': np.random.poisson(10, n_samples),
            'home_yellow': np.random.poisson(1, n_samples),
            'home_red': np.random.binomial(1, 0.1, n_samples),
            'away_shots': np.random.poisson(12, n_samples),
            'away_shots_on_target': np.random.poisson(4, n_samples),
            'away_corners': np.random.poisson(4, n_samples),
            'away_fouls_committed': np.random.poisson(11, n_samples),
            'away_yellow': np.random.poisson(1, n_samples),
            'away_red': np.random.binomial(1, 0.1, n_samples),
        })
        print(f"Generated {n_samples} synthetic matches with required columns")
    
    print("\n[3/5] Building features...")
    feature_data = build_features(clean_data)
    print(f"Features built: {feature_data.shape}")
    
    print("\n[4/5] Training and evaluating Poisson model...")
    
    if 'season' in feature_data.columns:
        train_poisson = feature_data[feature_data['season'] != '2526']
        test_poisson = feature_data[feature_data['season'] == '2526']
        print(f"Training on seasons: {feature_data['season'].unique().tolist()}")
        print(f"Test season: 2526")
    else:
        print("Warning: No season column found, using chronological split")
        train_poisson = feature_data.iloc[:int(len(feature_data) * 0.8)]
        test_poisson = feature_data.iloc[int(len(feature_data) * 0.8):]
    
    print(f"Poisson train: {len(train_poisson)}, test: {len(test_poisson)}")
    
    print("Training Poisson model...")
    poisson_model = fit_poisson_model(train_poisson)
    print("Poisson model trained")
    
    print("Generating Poisson predictions...")
    poisson_predictions = []
    for idx, (_, row) in enumerate(test_poisson.iterrows()):
        if idx >= 50:
            print(f"Stopped at {idx} predictions for speed test")
            break
        pred = predict_match(row['home_team'], row['away_team'], poisson_model)
        poisson_predictions.append(pred)
        if idx % 10 == 0:
            print(f"  Generated {idx} predictions...")
    
    test_subset = test_poisson.iloc[:len(poisson_predictions)]
    poisson_metrics = evaluate_poisson_model(test_subset, poisson_predictions)
    print(f"Poisson accuracy: {poisson_metrics['accuracy']:.4f}")
    print(f"Poisson Brier score: {poisson_metrics['brier']:.4f}")
    
    print("\n[5/5] Training and evaluating Random Forest model...")
    
    rf_model, label_encoder, X_test_rf, y_test_rf = train_random_forest(feature_data)
    
    rf_metrics = evaluate_random_forest(rf_model, label_encoder, X_test_rf, y_test_rf)
    print(f"Random Forest accuracy: {rf_metrics['accuracy']:.4f}")
    
    print("\nMODEL COMPARISON RESULTS")
    print(f"Poisson Accuracy:      {poisson_metrics['accuracy']:.4f} ({poisson_metrics['accuracy']*100:.2f}%)")
    print(f"Random Forest Accuracy: {rf_metrics['accuracy']:.4f} ({rf_metrics['accuracy']*100:.2f}%)")
    
    diff = rf_metrics['accuracy'] - poisson_metrics['accuracy']
    print(f"\nDifference: {diff:+.4f} ({diff*100:+.2f}%)")
    
    if diff > 0:
        print("\nRandom Forest performs better")
        print("-> Use Random Forest for production")
    elif diff < 0:
        print("\nPoisson performs better")
        print("-> Use Poisson for production")
    else:
        print("\nBoth models perform equally")
    
    print("\nTEST COMPLETE")
    
    results = {
        'poisson_accuracy': poisson_metrics['accuracy'],
        'rf_accuracy': rf_metrics['accuracy'],
        'best_model': 'rf' if diff > 0 else 'poisson'
    }
    
    import json
    results_path = '../../artifacts/model_comparison.json'
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
