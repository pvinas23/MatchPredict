"""Helpers for team metadata and upcoming matches."""

from pathlib import Path

import pandas as pd

# Team name to abbreviation mapping
TEAM_ABBREVIATIONS = {
    'Arsenal': 'ARS',
    'Aston Villa': 'AVL',
    'Bournemouth': 'BOU',
    'Brentford': 'BRE',
    'Brighton': 'BHA',
    'Chelsea': 'CHE',
    'Crystal Palace': 'CRY',
    'Coventry': 'COV',
    'Coventry City': 'COV',
    'Everton': 'EVE',
    'Fulham': 'FUL',
    'Hull': 'HUL',
    'Hull City': 'HUL',
    'Ipswich': 'IPS',
    'Ipswich Town': 'IPS',
    'Leeds': 'LEE',
    'Leicester': 'LEI',
    'Leicester City': 'LEI',
    'Liverpool': 'LIV',
    'Man City': 'MCI',
    'Manchester City': 'MCI',
    'Man Utd': 'MUN',
    'Man United': 'MUN',
    'Manchester United': 'MUN',
    'Newcastle': 'NEW',
    "Nott'm Forest": 'NFO',
    'Nottingham Forest': 'NFO',
    'Southampton': 'SOU',
    'Sunderland': 'SUN',
    'Spurs': 'TOT',
    'Tottenham': 'TOT',
    'West Ham': 'WHU',
    'Wolves': 'WOL'
}

# Abbreviation to SVG filename mapping
TEAM_SVG_MAP = {
    'ARS': 'arsenal.svg',
    'AVL': 'aston_villa.svg',
    'BOU': 'bournemouth.svg',
    'BRE': 'brentford.svg',
    'BHA': 'brighton.svg',
    'CHE': 'chelsea.svg',
    'CRY': 'crystal_palace.svg',
    'COV': 'coventry_city.svg',
    'EVE': 'everton.svg',
    'FUL': 'fulham.svg',
    'HUL': 'hull_city.svg',
    'IPS': 'ipswich.svg',
    'LEE': 'leeds_united.svg',
    'LEI': 'leicester_city.svg',
    'LIV': 'liverpool.svg',
    'MCI': 'machelor_city.svg',  # Note: filename has typo in original file
    'MUN': 'manchester_united.svg',
    'NEW': 'newcastle.svg',
    'NFO': 'nottingham_forest.svg',
    'SOU': 'southampton.svg',
    'SUN': 'sunderland.svg',
    'TOT': 'tottenham.svg',
    'WHU': 'west_ham.svg',
    'WOL': 'wolves.svg'
}

def get_team_svg(abbreviation):
    """Get SVG filename for a team abbreviation.
    
    Args:
        abbreviation (str): 3-letter abbreviation
    
    Returns:
        str: SVG filename or default if not found
    """
    return TEAM_SVG_MAP.get(abbreviation, 'premier_league.svg')

def get_team_abbreviation(team_name):
    """Get 3-letter abbreviation for a team name.
    
    Args:
        team_name (str): Full team name
    
    Returns:
        str: 3-letter abbreviation or first 3 letters if not found
    """
    return TEAM_ABBREVIATIONS.get(team_name, team_name[:3].upper())

# Explicit reverse mapping: abbreviation to full name (using names from historical data)
ABBREVIATION_TO_TEAM = {
    'ARS': 'Arsenal',
    'AVL': 'Aston Villa',
    'BOU': 'Bournemouth',
    'BRE': 'Brentford',
    'BHA': 'Brighton',
    'CHE': 'Chelsea',
    'CRY': 'Crystal Palace',
    'COV': 'Coventry City',
    'EVE': 'Everton',
    'FUL': 'Fulham',
    'HUL': 'Hull',  # Changed from Hull City to Hull (CSV name)
    'IPS': 'Ipswich',
    'LEE': 'Leeds',
    'LEI': 'Leicester',
    'LIV': 'Liverpool',
    'MCI': 'Man City',
    'MUN': 'Man United',  # This must match historical data exactly
    'NEW': 'Newcastle',
    'NFO': "Nott'm Forest",
    'SOU': 'Southampton',
    'SUN': 'Sunderland',
    'TOT': 'Tottenham',
    'WHU': 'West Ham',
    'WOL': 'Wolves'
}

def get_full_team_name(abbreviation):
    """Get full team name from abbreviation.
    
    Args:
        abbreviation (str): 3-letter abbreviation
    
    Returns:
        str: Full team name or abbreviation if not found
    """
    return ABBREVIATION_TO_TEAM.get(abbreviation, abbreviation)

def get_next_matches(limit=4):
    """Return the next upcoming matches from the raw CSV file."""
    csv_route = Path(__file__).resolve().parent / "data" / "raw" / "2026-2027_matches.csv"
    if not csv_route.exists():
        print(f"CSV file not found: {csv_route}")
        return []

    df = pd.read_csv(csv_route)
    if "Date" not in df.columns:
        print("CSV file does not contain a Date column")
        return []

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df[df["Date"] >= pd.Timestamp.today().normalize()]
    df = df.sort_values("Date").head(limit)

    result = []
    for _, row in df.iterrows():
        result.append(
            {
                "home_team": get_team_abbreviation(row["Home Team"]),
                "away_team": get_team_abbreviation(row["Away Team"]),
                "date": row["Date"].strftime("%Y-%m-%d"),
                "matchday": row["Round Number"],
            }
        )

    return result