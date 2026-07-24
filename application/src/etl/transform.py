"""Clean raw football data for feature engineering."""

from __future__ import annotations

import pandas as pd


RAW_COLUMN_MAP = {
    "date": "date",
    "hometeam": "home_team",
    "awayteam": "away_team",
    "ftr": "result",
    "fthg": "home_goals",
    "ftag": "away_goals",
    "hs": "home_shots",
    "as": "away_shots",
    "hst": "home_shots_on_target",
    "ast": "away_shots_on_target",
    "hc": "home_corners",
    "ac": "away_corners",
    "hf": "home_fouls_committed",
    "af": "away_fouls_committed",
    "hy": "home_yellow",
    "ay": "away_yellow",
    "hr": "home_red",
    "ar": "away_red",
}

TEXT_COLUMNS = ["home_team", "away_team", "result"]

NUMERIC_COLUMNS = [
    "home_goals",
    "away_goals",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_corners",
    "away_corners",
    "home_fouls_committed",
    "away_fouls_committed",
    "home_yellow",
    "away_yellow",
    "home_red",
    "away_red",
]

REQUIRED_COLUMNS = [
    "match_datetime",
    "home_team",
    "away_team",
    "result",
    "home_goals",
    "away_goals",
]


def clean_matches(raw_frame):
    """Clean raw match data and return a stable DataFrame."""
    if raw_frame is None:
        raise ValueError("raw_frame cannot be None")

    df = raw_frame.copy()

    season_column = None
    if 'season' in df.columns:
        season_column = df['season'].copy()

    lower_case_columns = {column.lower(): column for column in df.columns}
    selected_columns = [
        lower_case_columns[column]
        for column in RAW_COLUMN_MAP
        if column in lower_case_columns
    ]
    df = df[selected_columns]
    
    if season_column is not None:
        df['season'] = season_column
    df.rename(
        columns={
            lower_case_columns[column]: RAW_COLUMN_MAP[column]
            for column in RAW_COLUMN_MAP
            if column in lower_case_columns
        },
        inplace=True,
    )

    df["match_datetime"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df.drop(columns=["date"], errors="ignore", inplace=True)

    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = (
        df.dropna(subset=["match_datetime", "home_team", "away_team"])
        .sort_values(["match_datetime", "home_team", "away_team"])
        .reset_index(drop=True)
    )

    duplicate_subset = ["match_datetime", "home_team", "away_team"]
    if "season" in df.columns:
        duplicate_subset = ["season"] + duplicate_subset

    df = df.drop_duplicates(subset=duplicate_subset).reset_index(drop=True)

    return df


def validate_clean_frame(clean_frame):
    """Validate that the clean DataFrame meets basic requirements."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in clean_frame.columns]
    if missing_columns:
        raise ValueError(f"clean_frame is missing required columns: {missing_columns}")

    null_count = clean_frame[REQUIRED_COLUMNS].isna().sum().sum()
    if null_count:
        raise ValueError(f"clean_frame has {null_count} missing values in required columns")

    duplicate_subset = ["match_datetime", "home_team", "away_team"]
    if "season" in clean_frame.columns:
        duplicate_subset = ["season"] + duplicate_subset

    duplicates = clean_frame.duplicated(subset=duplicate_subset)
    duplicate_count = int(duplicates.sum())
    if duplicate_count:
        raise ValueError(f"clean_frame contains {duplicate_count} duplicate matches")

    return True

