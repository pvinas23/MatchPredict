"""Load cleaned football data into MySQL."""

from pathlib import Path
import sys

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from config import RAW_DATA_DIR  # noqa: E402
from src.etl.extract import load_all_seasons  # noqa: E402
from src.etl.transform import clean_matches, validate_clean_frame  # noqa: E402
from src.etl.features import build_features  # noqa: E402
from src.etl.load import load_to_mysql, save_to_csv  # noqa: E402


def _load_raw_season_files():
    """Load all season CSV files from the raw data folder."""
    files = sorted(RAW_DATA_DIR.glob("season_*.csv"))
    if not files:
        return pd.DataFrame()

    frames = []
    for file_path in files:
        df = pd.read_csv(file_path).assign(season=file_path.stem.replace("season_", ""))
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def main():
    """Run the CSV to MySQL load process."""
    print("Loading raw season files...")
    raw_frame = _load_raw_season_files()

    if raw_frame.empty:
        print("No local raw files found. Downloading seasons first...")
        load_all_seasons(["1920", "2021", "2122", "2223", "2324", "2425", "2526"])
        raw_frame = _load_raw_season_files()

    if raw_frame.empty:
        print("No raw data available. Aborting.")
        return

    print(f"Raw rows loaded: {len(raw_frame)}")
    clean_frame = clean_matches(raw_frame)
    validate_clean_frame(clean_frame)
    feature_frame = build_features(clean_frame)

    save_to_csv(clean_frame)

    print("Loading data into MySQL...")
    counts = load_to_mysql(clean_frame, feature_frame, raw_frame)

    print("Load complete")
    print(counts)


if __name__ == "__main__":
    main()