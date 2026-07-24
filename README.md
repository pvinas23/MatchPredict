# MatchPredict - Football Match Prediction System

## Overview

MatchPredict is a comprehensive football match prediction system that combines statistical modeling, machine learning, and web application development. This project serves as the final step for both **CS50 SQL** and **CS50x** courses, as well as for continue developing my skills at data bases, machine learning and web development.

The system predicts match outcomes for the English Premier League using historical data, featuring two complementary prediction models:
- **Poisson Model**: Statistical baseline using goal distribution analysis
- **Random Forest**: Machine learning model with engineered features

## Project Structure

This project is organized into two main directories to align with the course scopes:

### database/ (Database Layer)
- **Purpose**: Relational database design and analytical queries
- **Components**: Schema design, normalization, indexes, and complex SQL queries
- **Focus**: Data modeling, constraints, and database optimization

### application/ (Application Layer)
- **Purpose**: Data pipeline, predictive models, and web interface
- **Components**: ETL pipeline, ML models, Flask web application
- **Focus**: Data engineering, machine learning, and full-stack development

## Architecture

### Data Pipeline
```
Raw Data → Extraction → Cleaning → Feature Engineering → Modeling → Web Application
```

### Technology Stack
- **Backend**: Python 3.11, Flask
- **Database**: MySQL with optimized schema
- **ML/Stats**: scikit-learn, scipy, pandas, numpy
- **Data Processing**: pandas for ETL and feature engineering
- **Frontend**: HTML/CSS with responsive design

### Key Components

#### ETL Pipeline (`src/etl/`)
- **extract.py**: Data loading from multiple season CSV files
- **transform.py**: Data cleaning, validation, and standardization
- **features.py**: Feature engineering including rolling statistics and ELO ratings
- **load.py**: MySQL database population with cleaned data

#### Predictive Models (`src/models/`)
- **poisson.py**: Statistical model using Poisson distribution for goal probabilities
- **random_forest.py**: Machine learning model with engineered features and team data penalty system

#### Web Application (`app.py`)
- Flask-based dashboard for match predictions
- Real-time probability display for upcoming matches
- Featured match selection based on importance scores

## Features

### Prediction Models
- **Poisson Model**: 
  - Calculates expected goals based on team attack/defense parameters
  - Uses multiplicative model for realistic probability distribution
  - Serves as statistical baseline with ~46% accuracy

- **Random Forest**:
  - Ensemble classifier with engineered features (rolling stats, ELO ratings)
  - Optimized hyperparameters for balanced performance
  - Team data penalty system for newly promoted teams
  - Achieves ~55% accuracy on test data

### Data Engineering
- Rolling window statistics (5-match averages)
- ELO rating system for team strength assessment
- Feature engineering for shots, corners, fouls, and points
- Data validation and cleaning pipeline

### Web Interface
- Dashboard showing upcoming Premier League matches
- Real-time prediction probabilities for each match
- Featured match highlighting based on importance
- Responsive design with team logos

## Installation

### Prerequisites
- Python 3.11+
- MySQL 8.0+
- pip

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd MatchPredict
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r application/requirements.txt
```

4. **Configure environment**
```bash
cp application/.env.example application/.env
# Edit application/.env with your MySQL credentials
```

5. **Set up database**
```bash
# Run the schema from database
mysql -u your_user -p < database/schema.sql
```

6. **Load data**
```bash
cd application
python scripts/load_mysql.py
cd ..
```

## Usage

### Running the Web Application
```bash
cd application
python app.py
```
Access the application at `http://127.0.0.1:5000`

### Training Models
```bash
cd application
python evaluate_models.py
```

### Data Pipeline
```bash
# Load historical data into MySQL
python scripts/load_mysql.py
```

## Project Highlights

### Technical Achievements
- **Database Design**: Normalized schema with proper constraints and indexes
- **Data Pipeline**: Reproducible ETL process with validation at each stage
- **Model Performance**: Random Forest achieves 55% accuracy, Poisson 46%
- **Feature Engineering**: Rolling statistics and ELO ratings for team strength
- **Team Penalty System**: Handles newly promoted teams with realistic probability adjustments

### Code Quality
- Modular architecture with clear separation of concerns
- Comprehensive error handling and data validation
- Clean code style without narrative comments
- Professional project structure following industry standards

### Learning Outcomes
- **CS50 SQL**: Database design, normalization, complex queries, optimization
- **CS50x**: Data engineering, machine learning, web development, API design

## Data Sources
- Historical Premier League match data (2019/20 - 2025/26 seasons)
- Upcoming match schedules for 2026/27 season
- Team statistics including shots, corners, fouls, and cards

## Future Enhancements
- Additional predictive models (XGBoost, neural networks)
- Real-time data integration with live match feeds
- User authentication and personalized predictions
- Historical accuracy tracking and model comparison
- API endpoints for external integrations

## Contributing
This is a project for educational purposes. The codebase demonstrates professional development practices and can serve as a reference for similar data engineering and machine learning projects.

## License
Educational project - Not for commercial use

## Contact
Developed as final project for CS50 SQL and CS50x courses.

---

**Note**: This project's main focus is to demonstrate the integration of database design, data engineering, machine learning, and web development skills acquired through the CS50 curriculum.
