"""Feature engineering for match prediction.

Builds rolling statistics and ELO ratings.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

ROLLING_WINDOWS = [5]
ELO_INITIAL = 1500
ELO_K_FACTOR = 32
FEATURES = [
    "goals_scored",
    "goals_conceded",
    "shots",
    "corners",
    "points"
]


def add_rolling_features(clean_frame: pd.DataFrame, window: int = 5) -> pd.DataFrame:

    df_home = clean_frame[
        [
            "match_datetime",
            "home_team",
            "away_team",
            "result",
            "home_goals",
            "away_goals",
            "home_shots",
            "home_shots_on_target",
            "home_corners",
            "home_fouls_committed",
            "home_yellow",
            "home_red",
        ]
    ].copy().rename(columns={
        "home_team": "team",
        "away_team": "opponent",
        "result": "points",
        "home_goals": "goals_scored",
        "away_goals": "goals_conceded",
        "home_shots": "shots",
        "home_shots_on_target": "shots_on_target",
        "home_corners": "corners",
        "home_fouls_committed": "fouls_committed",
        "home_yellow": "yellow",
        "home_red": "red",
    })

    df_home["points"] = df_home["points"].map({"H": 3, "D": 1, "A": 0})

    df_away = clean_frame[
        [
            "match_datetime",
            "home_team",
            "away_team",
            "result",
            "home_goals",
            "away_goals",
            "away_shots",
            "away_shots_on_target",
            "away_corners",
            "away_fouls_committed",
            "away_yellow",
            "away_red",
        ]
    ].copy().rename(columns={
        "away_team": "team",
        "home_team": "opponent",
        "result": "points",
        "away_goals": "goals_scored",
        "home_goals": "goals_conceded",
        "away_shots": "shots",
        "away_shots_on_target": "shots_on_target",
        "away_corners": "corners",
        "away_fouls_committed": "fouls_committed",
        "away_yellow": "yellow",
        "away_red": "red",
    })

    df_away["points"] = df_away["points"].map({"A": 3, "D": 1, "H": 0})

    df_home["is_home"] = True
    df_away["is_home"] = False

    long_df = pd.concat([df_home, df_away], ignore_index=True)

    long_df = (
        long_df
        .sort_values(["team", "match_datetime"])
        .reset_index(drop=True)
    )

    for feature in FEATURES:

        previous = long_df.groupby("team")[feature].shift(1)

        long_df[f"avg_{feature}_last_{window}_matches"] = (
            previous
            .groupby(long_df["team"])
            .rolling(window=window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
            .round(2)
        )

    rolling_columns = [
        f"avg_{feature}_last_{window}_matches"
        for feature in FEATURES
    ]

    home_features = (
        long_df[long_df["is_home"]]
        [["match_datetime", "team"] + rolling_columns]
        .rename(
            columns={
                "team": "home_team",
                **{
                    col: f"{col}_home"
                    for col in rolling_columns
                }
            }
        )
    )

    away_features = (
        long_df[~long_df["is_home"]]
        [["match_datetime", "team"] + rolling_columns]
        .rename(
            columns={
                "team": "away_team",
                **{
                    col: f"{col}_away"
                    for col in rolling_columns
                }
            }
        )
    )

    clean_frame = clean_frame.merge(
        home_features,
        on=["match_datetime", "home_team"],
        how="left"
    )

    clean_frame = clean_frame.merge(
        away_features,
        on=["match_datetime", "away_team"],
        how="left"
    )

    return clean_frame


def calculate_elo(clean_frame: pd.DataFrame, k: int = ELO_K_FACTOR, 
                  initial_elo: int = ELO_INITIAL) -> pd.DataFrame:
    """
    Calculate ELO ratings for all teams.
    """
    df = clean_frame.sort_values('match_datetime').copy()
    
    elo_dict = {}
    elo_home_list = []
    elo_away_list = []
    
    for idx in range(len(df)):
        home_team = df.iloc[idx]['home_team']
        away_team = df.iloc[idx]['away_team']
        result = df.iloc[idx]['result']
        
        elo_home = elo_dict.get(home_team, initial_elo)
        elo_away = elo_dict.get(away_team, initial_elo)
        
        elo_home_list.append(elo_home)
        elo_away_list.append(elo_away)
        
        expected_home = 1 / (1 + 10 ** ((elo_away - elo_home) / 400))
        expected_away = 1 - expected_home
        
        if result == 'H':
            actual_home, actual_away = 1.0, 0.0
        elif result == 'D':
            actual_home, actual_away = 0.5, 0.5
        else:
            actual_home, actual_away = 0.0, 1.0
        
        elo_dict[home_team] = elo_home + k * (actual_home - expected_home)
        elo_dict[away_team] = elo_away + k * (actual_away - expected_away)
    
    df['elo_home_pre'] = elo_home_list
    df['elo_away_pre'] = elo_away_list
    df['elo_diff'] = df['elo_home_pre'] - df['elo_away_pre']
    
    print(f"ELO calculated: min={min(elo_dict.values()):.1f}, max={max(elo_dict.values()):.1f}")
    
    return df


    


def build_features(clean_frame: pd.DataFrame) -> pd.DataFrame:
    """Build features for modeling."""
    df = clean_frame.copy()
    
    print(f"Starting feature engineering. Shape: {df.shape}")
    
    for window in ROLLING_WINDOWS:
        df = add_rolling_features(df, window=window)
        print(f"Added rolling features with window={window}")
    
    df = calculate_elo(df)
    print("Added ELO features")
    
    print(f"Feature engineering complete. Final shape: {df.shape}")
    
    return df


def split_features_targets(feature_frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Separate features from target for modeling."""
    exclude_cols = [
        'match_datetime', 'home_team', 'away_team', 'result',
        'home_goals', 'away_goals', 'season'
    ]
    
    feature_cols = [col for col in feature_frame.columns 
                   if col not in exclude_cols and feature_frame[col].dtype in ['int64', 'float64']]
    
    X = feature_frame[feature_cols].fillna(0)
    y = feature_frame['result']
    
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"Features: {feature_cols}")
    
    return X, y
