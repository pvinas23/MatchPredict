"""Save cleaned data to CSV and load data into MySQL."""

from pathlib import Path

import pandas as pd

from config import PROCESSED_DATA_DIR
from src.db.connection import mysql_session, run_query


def save_to_csv(clean_frame, filename="cleaned_matches.csv"):
    """Save cleaned data to CSV."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROCESSED_DATA_DIR / filename
    
    clean_frame.to_csv(filepath, index=False)
    print(f"Saved {len(clean_frame)} rows to {filepath}")
    
    return filepath


def load_from_csv(filename="cleaned_matches.csv"):
    """Load cleaned data from CSV."""
    filepath = PROCESSED_DATA_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df['match_datetime'] = pd.to_datetime(df['match_datetime'])
    
    print(f"Loaded {len(df)} rows from {filepath}")
    
    return df


def _season_name_from_code(season_code):
    """Return a display season name from a compact season code."""
    text = str(season_code).strip()
    if len(text) != 4 or not text.isdigit():
        return text

    start_year = 2000 + int(text[:2])
    end_year = start_year + 1
    return f"{start_year}/{end_year}"


def _build_season_lookup(clean_frame):
    """Map season codes to display names."""
    if "season" not in clean_frame.columns:
        return {}

    season_values = clean_frame["season"].dropna().astype(str).unique().tolist()
    return {season: _season_name_from_code(season) for season in season_values}


def _fetch_id_map(connection, table_name):
    """Fetch an id map for a simple lookup table."""
    rows = run_query(connection, f"SELECT id, name FROM {table_name}")
    return {row["name"]: row["id"] for row in rows}


def _mean_from_columns(row, columns):
    """Return the mean of the numeric values found in the given columns."""
    values = []
    for column in columns:
        value = row.get(column)
        if pd.notna(value):
            values.append(float(value))

    if not values:
        return None

    return round(sum(values) / len(values), 3)


def load_to_mysql(clean_frame, feature_frame=None, raw_frame=None):
    """Load cleaned matches and optional features into MySQL."""
    if clean_frame is None or clean_frame.empty:
        print("No cleaned data available for MySQL load")
        return {
            "leagues": 0,
            "seasons": 0,
            "teams": 0,
            "matches": 0,
            "match_stats": 0,
            "team_ratings": 0,
        }

    frame = clean_frame.copy()
    raw_lookup = {}
    if raw_frame is not None and not raw_frame.empty:
        raw_copy = raw_frame.copy()
        if "Date" in raw_copy.columns:
            raw_copy["Date"] = pd.to_datetime(raw_copy["Date"], errors="coerce")
        if "season" in raw_copy.columns:
            raw_copy["season"] = raw_copy["season"].astype(str)
        for _, raw_row in raw_copy.iterrows():
            raw_date = pd.to_datetime(raw_row.get("Date"), errors="coerce")
            raw_key = (
                str(raw_row.get("season", "")).strip(),
                raw_date.to_pydatetime() if pd.notna(raw_date) else None,
                str(raw_row.get("HomeTeam", "")).strip(),
                str(raw_row.get("AwayTeam", "")).strip(),
            )
            raw_lookup[raw_key] = raw_row

    if feature_frame is not None and not feature_frame.empty:
        if "match_datetime" in feature_frame.columns:
            feature_frame = feature_frame.copy()
            feature_frame["match_datetime"] = pd.to_datetime(feature_frame["match_datetime"], errors="coerce")

    season_lookup = _build_season_lookup(frame)

    match_columns = [
        "match_datetime",
        "home_team",
        "away_team",
        "result",
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
        "season",
    ]
    available_columns = [column for column in match_columns if column in frame.columns]
    frame = frame[available_columns].copy()

    if "match_datetime" in frame.columns:
        frame["match_datetime"] = pd.to_datetime(frame["match_datetime"], errors="coerce")
        frame = frame.dropna(subset=["match_datetime", "home_team", "away_team"])

    with mysql_session() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT IGNORE INTO leagues (name, country, tier)
                VALUES (%s, %s, %s)
                """,
                ("Premier League", "England", 1),
            )
            connection.commit()
            leagues_loaded = cursor.rowcount

            league_id = run_query(
                connection,
                "SELECT id FROM leagues WHERE name = %s",
                ("Premier League",),
            )[0]["id"]

            season_rows = []
            for season_code, season_name in season_lookup.items():
                season_rows.append((league_id, season_name))

            if season_rows:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO seasons (league_id, name)
                    VALUES (%s, %s)
                    """,
                    season_rows,
                )
                connection.commit()

            season_map = {
                row["name"]: row["id"]
                for row in run_query(connection, "SELECT id, name FROM seasons WHERE league_id = %s", (league_id,))
            }

            team_names = pd.unique(frame[["home_team", "away_team"]].values.ravel("K"))
            team_rows = [(str(name).strip(),) for name in team_names if pd.notna(name) and str(name).strip()]
            if team_rows:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO teams (name)
                    VALUES (%s)
                    """,
                    team_rows,
                )
                connection.commit()

            team_map = _fetch_id_map(connection, "teams")

            match_rows = []
            match_stats_payload = []
            odds_payload = []
            team_rating_rows = []
            match_keys = []

            for _, row in frame.iterrows():
                season_code = str(row.get("season", "")).strip()
                season_name = season_lookup.get(season_code)
                if season_name is None:
                    season_name = season_code

                season_id = season_map.get(season_name)
                if season_id is None:
                    continue

                home_team = str(row["home_team"]).strip()
                away_team = str(row["away_team"]).strip()
                home_team_id = team_map.get(home_team)
                away_team_id = team_map.get(away_team)
                if home_team_id is None or away_team_id is None:
                    continue

                match_datetime = pd.to_datetime(row["match_datetime"], errors="coerce")
                if pd.isna(match_datetime):
                    continue

                match_rows.append(
                    (
                        season_id,
                        match_datetime.to_pydatetime(),
                        home_team_id,
                        away_team_id,
                        int(row["home_goals"]),
                        int(row["away_goals"]),
                        row["result"],
                    )
                )

                match_keys.append((season_id, match_datetime.to_pydatetime(), home_team_id, away_team_id))

                match_stats_payload.append(
                    (
                        match_keys[-1],
                        (
                            int(row["home_shots"]) if "home_shots" in row and pd.notna(row.get("home_shots")) else None,
                            int(row["home_shots_on_target"]) if "home_shots_on_target" in row and pd.notna(row.get("home_shots_on_target")) else None,
                            None,
                            int(row["home_corners"]) if "home_corners" in row and pd.notna(row.get("home_corners")) else None,
                            int(row["home_fouls_committed"]) if "home_fouls_committed" in row and pd.notna(row.get("home_fouls_committed")) else None,
                            None,
                            None,
                            int(row["home_yellow"]) if "home_yellow" in row and pd.notna(row.get("home_yellow")) else None,
                            int(row["home_red"]) if "home_red" in row and pd.notna(row.get("home_red")) else None,
                            int(row["away_shots"]) if "away_shots" in row and pd.notna(row.get("away_shots")) else None,
                            int(row["away_shots_on_target"]) if "away_shots_on_target" in row and pd.notna(row.get("away_shots_on_target")) else None,
                            None,
                            int(row["away_corners"]) if "away_corners" in row and pd.notna(row.get("away_corners")) else None,
                            int(row["away_fouls_committed"]) if "away_fouls_committed" in row and pd.notna(row.get("away_fouls_committed")) else None,
                            None,
                            None,
                            int(row["away_yellow"]) if "away_yellow" in row and pd.notna(row.get("away_yellow")) else None,
                            int(row["away_red"]) if "away_red" in row and pd.notna(row.get("away_red")) else None,
                        ),
                    )
                )

                if feature_frame is not None and not feature_frame.empty:
                    feature_row = feature_frame[
                        (feature_frame["match_datetime"] == match_datetime)
                        & (feature_frame["home_team"] == home_team)
                        & (feature_frame["away_team"] == away_team)
                    ]
                    if not feature_row.empty:
                        feature_row = feature_row.iloc[0]
                        if "elo_home_pre" in feature_row and pd.notna(feature_row["elo_home_pre"]):
                            team_rating_rows.append((home_team_id, season_id, match_datetime.to_pydatetime(), float(feature_row["elo_home_pre"])) )
                        if "elo_away_pre" in feature_row and pd.notna(feature_row["elo_away_pre"]):
                            team_rating_rows.append((away_team_id, season_id, match_datetime.to_pydatetime(), float(feature_row["elo_away_pre"])) )

                if raw_lookup:
                    raw_key = (
                        season_code,
                        match_datetime.to_pydatetime(),
                        home_team,
                        away_team,
                    )
                    raw_row = raw_lookup.get(raw_key)
                    if raw_row is not None:
                        home_odds_columns = [column for column in raw_row.index if column.upper().endswith("H")]
                        draw_odds_columns = [column for column in raw_row.index if column.upper().endswith("D")]
                        away_odds_columns = [column for column in raw_row.index if column.upper().endswith("A")]

                        b365_home = raw_row.get("B365H")
                        b365_draw = raw_row.get("B365D")
                        b365_away = raw_row.get("B365A")

                        odds_payload.append(
                            (
                                match_keys[-1],
                                b365_home if pd.notna(b365_home) else None,
                                b365_draw if pd.notna(b365_draw) else None,
                                b365_away if pd.notna(b365_away) else None,
                                _mean_from_columns(raw_row, home_odds_columns),
                                _mean_from_columns(raw_row, draw_odds_columns),
                                _mean_from_columns(raw_row, away_odds_columns),
                            )
                        )

            if match_rows:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO matches (
                        season_id, date, home_team_id, away_team_id,
                        home_team_goals, away_team_goals, result
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    match_rows,
                )
                connection.commit()

            match_id_map = {}
            inserted_matches = run_query(
                connection,
                """
                SELECT id, season_id, date, home_team_id, away_team_id
                FROM matches
                """,
            )
            for match_row in inserted_matches:
                key = (
                    match_row["season_id"],
                    match_row["date"].to_pydatetime() if hasattr(match_row["date"], "to_pydatetime") else match_row["date"],
                    match_row["home_team_id"],
                    match_row["away_team_id"],
                )
                match_id_map[key] = match_row["id"]

            if match_stats_payload:
                stats_insert_rows = []
                for match_key, stats_row in match_stats_payload:
                    match_id = match_id_map.get(match_key)
                    if match_id is None:
                        continue
                    stats_insert_rows.append((match_id, *stats_row))

                cursor.executemany(
                    """
                    INSERT IGNORE INTO match_stats (
                        match_id, home_shots, home_shots_on_target, home_shots_hit_woodwork,
                        home_corners, home_fouls_committed, home_free_kicks_conceded, home_offsides,
                        home_yellow, home_red, away_shots, away_shots_on_target,
                        away_shots_hit_woodwork, away_corners, away_fouls_committed,
                        away_free_kicks_conceded, away_offsides, away_yellow, away_red
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    stats_insert_rows,
                )
                connection.commit()

            if odds_payload:
                odds_insert_rows = []
                for match_key, b365_home, b365_draw, b365_away, avg_home, avg_draw, avg_away in odds_payload:
                    match_id = match_id_map.get(match_key)
                    if match_id is None:
                        continue
                    odds_insert_rows.append(
                        (
                            match_id,
                            b365_home,
                            b365_draw,
                            b365_away,
                            avg_home,
                            avg_draw,
                            avg_away,
                        )
                    )

                cursor.executemany(
                    """
                    INSERT IGNORE INTO match_market_odds (
                        match_id, b365_home_win_odds, b365_draw_odds, b365_away_win_odds,
                        market_avg_home_win_odds, market_avg_draw_odds, market_avg_away_win_odds
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    odds_insert_rows,
                )
                connection.commit()

            if team_rating_rows:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO team_ratings (team_id, season_id, date, rating)
                    VALUES (%s, %s, %s, %s)
                    """,
                    team_rating_rows,
                )
                connection.commit()

            return {
                "leagues": int(leagues_loaded),
                "seasons": len(season_rows),
                "teams": len(team_rows),
                "matches": len(match_rows),
                "match_stats": len(match_stats_payload),
                "market_odds": len(odds_payload),
                "team_ratings": len(team_rating_rows),
            }
        finally:
            cursor.close()
