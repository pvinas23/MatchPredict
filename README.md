# MatchPredict

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

> **Note:** The web application is best viewed at 50% zoom in your browser for optimal layout.

Premier League match prediction: a data pipeline that pulls seven seasons of historical results, a normalised MySQL database designed from scratch, two prediction models evaluated honestly on a held-out season, and a Flask dashboard showing live predictions for upcoming matches.

Built as the final project for Harvard's CS50x (application layer) and CS50 SQL (database layer).

## What It Does

The web app currently has two working sections:

### 1. Dashboard

The four next upcoming matches with outcome probabilities, the random forest's accuracy, a key match of the next matchday picked by team strength and how balanced the tie is, and the current state of the data pipeline.

<img width="1632" height="722" alt="image" src="https://github.com/user-attachments/assets/57bd40df-3b5b-4c98-bee2-f7ce778da5d2" />

### 2. Model Showdown

Statistics about the accuracy of the random forest and the poisson models while trying to predict the outcome of the matches of the 25/26 season.

<img width="1618" height="889" alt="image" src="https://github.com/user-attachments/assets/d9049eef-0808-4ef6-87dd-250b53fa7f40" />

## Coming Later

Three more sections exist in the codebase as designed placeholders (styled "under construction" pages), but aren't implemented yet: a head-to-head Match Predictor, a Monte Carlo League Simulator, and an Architecture page documenting the pipeline. They're on the roadmap, not part of this release.

## Results

Both models are trained on seasons 2019/20 - 2024/25 and the last season is used to select the hyperparameters. The models then try to predict the outcome of the 2025/26 season and this is compared to the actual results to get their accuracy for the "Model Showdown" section.

| Model | Accuracy |
|-------|----------|
| Random Forest | 53.42% |
| Poisson (MLE) | 46.58% |
| Always predict home win | 42.6% |

To put these numbers into context, the bookmaker's favourite wins 54.5% of matches across all seven seasons (calculated via Query 6 in database/queries.sql). We can consider this a realistic performance ceiling for our models, whereas the random baseline stands at 33% accuracy (a 1 in 3 chance: H, A, or D).

These are honest, leakage-free numbers. Every feature is strictly pre-match: rolling form averages are lagged one game and Elo ratings are taken before kickoff. Match statistics such as shots or corners from the match being predicted are never used as features.

## The Models

### 1. Poisson Goal Model

Each team gets an attack and a defence strength in a log-linear model fitted by maximum likelihood (scipy.optimize):

```
log(λ_home) = μ + home_advantage + attack[home] − defence[away]
log(λ_away) = μ + attack[away] − defence[home]
```

Outcome probabilities come from the joint distribution of two independent Poisson goal counts.

### 2. Random Forest

A shallow forest over pre-match features: rolling 5-match averages of goals, shots, shots on target, corners and points, plus pre-match Elo ratings for both sides.

To avoid guessing randomly with newly promoted teams due to the absence of data, these get league-median form and a bottom-quartile strength prior.

## Database (CS50 SQL)

`database/schema.sql` is a normalised MySQL schema with foreign keys, check constraints, indexes for accelerating common query patterns, and views for match results and team statistics (8 tables — see the ER diagram in `database/DESIGN.md`). `database/queries.sql` contains the analytical queries used to produce the numbers above, including a league-table-at-date query and a comparison of the models against bookmaker odds.

The Flask app is connected to this database: on startup it tries to read historical matches from MySQL first, and only falls back to the raw CSVs in `data/raw/` if MySQL isn't reachable or hasn't been populated yet. This means the app works out of the box with no setup, but uses the proper relational database whenever it's available.

## Architecture

```
football-data.co.uk          fixture list
        │                         │
   src/etl/extract.py             │
        ▼                         ▼
   src/etl/transform.py    data/reference/
        ▼
   src/etl/load.py  ──►  MySQL (normalised schema, database/)
        │
        ▼
   src/db/queries.py  ──  reads matches back from MySQL
        │ (falls back to CSV if MySQL is unavailable/empty)
        ▼
   src/etl/features.py  ──  rolling form + Elo (strictly pre-match)
        ▼
   src/models/          ──  Poisson (MLE) + Random Forest
        ▼
   evaluate_models.py   ──►  artifacts/  (models + metrics)
        ▼
   app.py (Flask)       ──  reads MySQL, falls back to CSV
```

The two course scopes map to the two top-level directories:

- `application/` — CS50x final project: ETL pipeline, models, Flask app
- `database/` — CS50 SQL final project: schema, analytical queries, design document

## Getting Started

Requires Python 3.11+ and (optionally) MySQL 8+.

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r application/requirements.txt

# Train the models and generate metrics (downloads season data on first run)
cd application
python evaluate_models.py

# Run the web app
python app.py                    # http://127.0.0.1:5000
```

The app works without a database — it falls back to the raw CSVs. To use MySQL as the data source:

```bash
mysql -u <user> -p < ../database/schema.sql
cp .env.example .env             # then fill in your MySQL credentials
python scripts/load_mysql.py
```

Once loaded, `app.py` will pick up MySQL automatically on the next run — no code changes needed. You can also run the queries in `database/queries.sql` directly against MySQL to reproduce the analysis behind the results table above.

## Limitations
- Draws are structurally hard to call: the accuracy-maximising prediction is rarely a draw, so per-class draw accuracy is low for both models (in fact null due to how they work).
- No player-level data (injuries, transfers, lineups), which caps how far team-level form features can go.
- Bookmaker odds are stored in the database as a benchmark but deliberately kept out of the feature set, so the models stay independent of the market.
- Match Predictor, League Simulator, and Architecture pages are placeholders, not implemented.

## Acknowledgements
- Historical match data from football-data.co.uk
- Fixture list from fixturedownload.com
- Team's crests from football-logos.cc

AI assistance was used to review and refactor the codebase and documentation, in line with CS50's academic honesty policy on final projects. However, the design, implementation and decisions about the project are my own.

## License

MIT
