"""Read queries used by the Flask app.

Returns matches in the same schema produced by etl.transform.clean_matches,
so the feature pipeline works identically on both data sources.
"""

import pandas as pd

from .connection import mysql_session, run_query

_MATCHES_QUERY = """
    SELECT
        m.date AS match_datetime,
        th.name AS home_team,
        ta.name AS away_team,
        m.result,
        m.home_team_goals AS home_goals,
        m.away_team_goals AS away_goals,
        ms.home_shots, ms.away_shots,
        ms.home_shots_on_target, ms.away_shots_on_target,
        ms.home_corners, ms.away_corners,
        ms.home_fouls_committed, ms.away_fouls_committed,
        ms.home_yellow, ms.away_yellow,
        ms.home_red, ms.away_red,
        s.name AS season_name
    FROM matches AS m
    JOIN seasons AS s ON s.id = m.season_id
    JOIN teams AS th ON th.id = m.home_team_id
    JOIN teams AS ta ON ta.id = m.away_team_id
    LEFT JOIN match_stats AS ms ON ms.match_id = m.id
    ORDER BY m.date
"""


def _season_code(season_name):
    """Convert '2019/2020' to the compact '1920' code used by the pipeline."""
    parts = str(season_name).split("/")
    if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 4:
        return parts[0][2:] + parts[1][2:]
    return str(season_name)


def fetch_clean_matches():
    """Return all stored matches as a DataFrame, or None if the DB is empty."""
    with mysql_session() as connection:
        rows = run_query(connection, _MATCHES_QUERY)

    if not rows:
        return None

    frame = pd.DataFrame(rows)
    frame["match_datetime"] = pd.to_datetime(frame["match_datetime"])
    frame["season"] = frame["season_name"].map(_season_code)
    return frame.drop(columns=["season_name"])
