import os
from pathlib import Path
from dotenv import load_dotenv 

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REFERENCE_DATA_DIR = DATA_DIR / "reference"

SRC_DIR = BASE_DIR / "src"
ETL_DIR = SRC_DIR / "etl"
MODELS_DIR = SRC_DIR / "models"
DB_DIR = SRC_DIR / "db"

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
INSTANCE_DIR = BASE_DIR / "instance"

for folder in [LOGS_DIR, ARTIFACTS_DIR, INSTANCE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "matchpredict_user"),
    "password": os.getenv("MYSQL_PASSWORD", "change_me"),
    "database": os.getenv("MYSQL_DATABASE", "matchpredict"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
}

FLASK_SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
FLASK_ENV = os.getenv("FLASK_ENV", "development")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

