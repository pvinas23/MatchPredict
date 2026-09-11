"""Download football data from football-data.co.uk."""

from config import RAW_DATA_DIR
import requests


def download_season(season, output_dir="data/raw"):
    """Download one season of raw match data."""
    league = "E0"
    download_url = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
    final_route = RAW_DATA_DIR / f"season_{season}.csv"
    if final_route.exists():
        print(f"The {season} season's file already exists")
        return
    print(f"Downloading {season} season's data")
    response = requests.get(download_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download data for season {season}")
    with open(final_route, "wb") as file:
        file.write(response.content)
    print(f"Season {season} saved successfully")
    

def load_all_seasons(seasons):
    print("Starting season downloads")
    for season in seasons:
        try:
            download_season(season)
        except Exception as e:
            print(f"Download error for season {season}: {e}")
    print("Finished downloading all seasons")
