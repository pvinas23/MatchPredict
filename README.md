# MatchPredict

Premier League match prediction, end to end: a data pipeline that pulls seven seasons of historical results, a normalised MySQL database, two prediction models evaluated honestly on a held-out season, and a Flask web app with a live predictor and a Monte Carlo season simulator.

Built as the final project for Harvard's **CS50x** (application layer) and **CS50 SQL** (database layer).

## WHAT IT DOES
The web has 5 independent sections with distinct functionalities:

### 1. Dashboard
The four next upcoming matches with outcome probabilities, the random forest's accuracy, a key match of the next matchday picked by team strength and how balanced the tie is and the current state of the data pipeline.

<img width="1632" height="722" alt="image" src="https://github.com/user-attachments/assets/57bd40df-3b5b-4c98-bee2-f7ce778da5d2" />

### 2. Model showdown
Statistics about the accuracy of the random forest and the poisson models while trying to predict the outcome of the matches of the 25/26 season.

<img width="1618" height="889" alt="image" src="https://github.com/user-attachments/assets/d9049eef-0808-4ef6-87dd-250b53fa7f40" />

### 3. Match predictor
Head-to-head predictor, you can pick two teams and compare the model's predictions for a match between them, with expected goals and also head-to-head history.

<img width="1643" height="706" alt="image" src="https://github.com/user-attachments/assets/76890f24-f5a8-42de-ac55-76f35210a1e1" />

### 4. League Simulator
Monte Carlo simulation of the 2026/27 season: expected goals and goal difference and also title, top-4 and relegation probabilities per team.

<img width="1626" height="844" alt="image" src="https://github.com/user-attachments/assets/23322626-231c-44e2-b4f1-2b936bc79624" />

### 5. Architecture
A short explanation of the data pipeline, some deployment metadata and a few design decisions explained.

<img width="1645" height="560" alt="image" src="https://github.com/user-attachments/assets/ef4a4c6b-08c3-4eb5-83ff-89d3c3895852" />

## RESULTS

Both models are trained on seasons 2019/20 - 2024/25 and the last season is used to select the hyperparameters. The models then try to predict the outcome of the 2025/26 season and this is compared to the actual results to get their accuracy for the "Model Showdown" section.

| Model | Accuracy | Brier score |
| --- | --- | --- |
| Random Forest | **48.7%** | **0.626** |
| Poisson (MLE) | 47.1% | 0.635 |
| Always predict home win | 42.6% | - |

To put these numbers into context, the bookmaker's favourite wins 54.5% of matches across all seven seasons (calculated via Query 6 in database/queries.sql). We can consider this a realistic performance ceiling for our models, whereas the random baseline stands at 33% accuracy (a 1 in 3 chance: H, A, or D).

These are honest, leakage-free numbers. Every feature is strictly pre-match: rolling form averages are lagged one game and Elo ratings are taken before kickoff (for the model not to take into account the match it's trying to predict). Match statistics such as shots or corners from the match being predicted are never used as features — a test guards against reintroducing that leak.

## THE MODELS

**1. Poisson goal model** — each team gets an attack and a defence strength in a log-linear model fitted by maximum likelihood (`scipy.optimize`):

```text
log(λ_home) = μ + home_advantage + attack[home] − defence[away]
log(λ_away) = μ + attack[away] − defence[home]
```

Outcome probabilities come from the joint distribution of two independent Poisson goal counts. The same model powers the season simulator, which samples goals for every fixture and aggregates finishing positions across thousands of simulated seasons.

**2. Random Forest** — a shallow forest (200 trees, depth 6) over 15 pre-match features: rolling 5-match averages of goals, shots, shots on target, corners and points, plus pre-match Elo ratings for both sides.

To avoid guessing randomly with newly promoted teams due to the absence of data, these get league-median form and a bottom-quartile strength prior.

## Architecture

```text
football-data.co.uk          fixture list
        │                         │
   src/etl/extract.py             │
        ▼                         ▼
   src/etl/transform.py    data/reference/
        ▼
   src/etl/features.py  ──  rolling form + Elo (strictly pre-match)
        │
        ├──►  src/etl/load.py  ──►  MySQL (normalised schema, database/)
        │
        ▼
   src/models/          ──  Poisson (MLE) + Random Forest
        │
        ▼
   evaluate_models.py   ──►  artifacts/  (models + metrics)
        │
        ▼
   app.py (Flask)       ──  reads MySQL, falls back to CSV
```

The two course scopes map to the two top-level directories:

```
application/    CS50x final project  — ETL pipeline, models, Flask app, tests
database/       CS50 SQL final project — schema, analytical queries, design document
```

The database layer (`database/schema.sql`) is a normalised MySQL schema with foreign keys, check constraints, indexes for accelerating common query patterns, and views for match results and team statistics. `database/queries.sql` contains the analytical queries, including a league-table-at-date query and a comparison of the models against bookmaker odds. Finally, in `database/DESIGN.md` we can find all the design information about the database, as well as the ER diagram that contains the 8 tables.

## Getting started

Requires Python 3.11+ and (optionally) MySQL 8+.

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r application/requirements.txt

# Train the models and generate metrics (downloads season data on first run)
cd application
python evaluate_models.py

# Run the web app
python app.py                    # [http://127.0.0.1:5000](http://127.0.0.1:5000)
```

The app works without a database — it falls back to the raw CSVs. To use MySQL as the data source:

```bash
mysql -u <user> -p < ../database/schema.sql
cp .env.example .env             # then fill in your MySQL credentials
python scripts/load_mysql.py
```

## Tests

```bash
cd application
python -m pytest tests/
```

The suite covers the cleaning step, the feature pipeline (including a regression test that fails if post-match stats ever leak into the feature set), both models and the simulator.

## Limitations

- Draws are structurally hard to call: the accuracy-maximising prediction is rarely a draw, so per-class draw accuracy is low for both models (in fact null due to how they work)
- No player-level data (injuries, transfers, lineups), which caps how far team-level form features can go.
- Bookmaker odds are stored in the database as a benchmark but deliberately kept out of the feature set, so the models stay independent of the market.

## Acknowledgements

- Historical match data from [football-data.co.uk](https://www.football-data.co.uk/);
  fixture list from [fixturedownload.com](https://fixturedownload.com/);
  team's crests from [football-logos.cc](https://football-logos.cc/)
- AI assistance was used to review and refactor the codebase and documentation, in line with CS50's academic honesty policy on final projects. However, the design, implementation and decisions about the project are my own.

## License

[MIT](LICENSE)
