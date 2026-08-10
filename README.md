# Global Disaster Events Analysis — Final Project

**Name:** NKURANGA BAZIGA CALEB
**Student ID:** 28845
**Lecturer:** KAYITARE Elie
**Course:** Introduction to Big Data

A full data pipeline built on GDACS (Global Disaster Alert and Coordination System) data:
extract → clean → validate → load into PostgreSQL → explore → train machine learning models →
visualize in Tableau → ask questions with an AI assistant.

## What this project does

- Pulls disaster event data (earthquakes, floods, cyclones, droughts, volcanoes, wildfires)
  from the GDACS API, scoped to Orange and Red alert-level events, 2000–2024
- Cleans and validates the data, then loads it into PostgreSQL using a raw + cleaned table layout
- Explores the data (EDA) with summary stats and charts
- Trains two machine learning models (Logistic Regression, Random Forest) to predict whether
  an event is Orange or Red alert level
- Builds an interactive Tableau Public dashboard
- Includes a small AI assistant (Groq API) that answers plain-English questions about the data

## How to run this project

### 1. Set up the environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install requests pandas psycopg2-binary python-dotenv pytest matplotlib seaborn scikit-learn joblib groq
```

### 2. Create the database

In pgAdmin or `psql`:
```sql
CREATE DATABASE gdacs_disasters;
```

### 3. Set up your `.env` file

Create a `.env` file in the project root with:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gdacs_disasters
DB_USER=postgres
DB_PASSWORD=your_postgres_password
GROQ_API_KEY=your_groq_api_key
```

Get a free Groq API key at console.groq.com.

### 4. Run the pipeline

```powershell
python main.py
```

This extracts data from the GDACS API (or uses the cached copy in `data/gdacs_raw.json` if
already downloaded), cleans it, checks it for problems, and loads it into PostgreSQL. It's
safe to run more than once — it won't create duplicate rows, and it only loads new years on
later runs.

To force a fresh download instead of using the cache:
```powershell
python main.py --refresh
```

### 5. Run the EDA (exploratory data analysis)

```powershell
python eda_report.py
```

Prints a summary of the dataset and saves 6 charts into the `eda/` folder.

### 6. Train the machine learning models

```powershell
python train_models.py
python export_predictions.py
```

Trains Logistic Regression and Random Forest, saves the trained models into `models/`, and
exports the Random Forest's predictions to `data/ml_predictions.csv` for use in Tableau.

### 7. Try the AI assistant

```powershell
python ai_assistant.py
```

Type a plain-English question about the data (for example: "Which country had the most Red
alert events?") and get a plain-English answer back. Type `quit` to exit.

### 8. Run the automated tests

```powershell
pytest -v
```

## How data moves through this project

1. **API → raw file**: `extract.py` pulls data from the GDACS API and saves the untouched
   response to `data/gdacs_raw.json`
2. **Raw file → PostgreSQL raw table**: the untouched data is also saved into `raw_gdacs` in
   PostgreSQL, as a safety copy
3. **Raw → cleaned**: `transform.py` and `validate.py` clean and check the data, and
   `load.py` saves the result into `clean_gdacs` in PostgreSQL
4. **Cleaned data → EDA**: `eda_report.py` reads from `clean_gdacs` to produce summary
   statistics and charts
5. **Cleaned data → Machine Learning**: `train_models.py` reads from `clean_gdacs`, trains
   two models, and saves them into `models/`. `export_predictions.py` then uses the saved
   Random Forest model to generate `data/ml_predictions.csv`
6. **Cleaned data + predictions → Tableau**: both `data/gdacs_clean.csv` (exported from
   `clean_gdacs`) and `data/ml_predictions.csv` are connected to Tableau Public to build the
   dashboard
7. **Cleaned data → AI Assistant**: `ai_assistant.py` connects live to `clean_gdacs` in
   PostgreSQL, turning plain-English questions into SQL queries and the results back into
   plain-English answers

## Project files

| File | Purpose |
|---|---|
| `extract.py` | Downloads data from the GDACS API, with retries and local caching |
| `transform.py` | Cleans and flattens the raw data |
| `validate.py` | Checks the cleaned data for missing values, wrong types, and out-of-range values |
| `db.py` | Handles the PostgreSQL connection |
| `load.py` | Creates tables and loads data into PostgreSQL |
| `main.py` | Runs the full pipeline in order, with logging |
| `eda_report.py` | Produces summary stats and charts |
| `train_models.py` | Trains and evaluates the two ML models |
| `export_predictions.py` | Exports the Random Forest's predictions for Tableau |
| `ai_assistant.py` | The plain-English question-answering assistant |
| `run_pipeline.bat` | Batch file used to run the pipeline automatically (Windows Task Scheduler) |
| `tests/` | Automated tests for cleaning, validation, and the AI assistant |
| `data_dictionary.md` | Column-by-column description of the cleaned dataset |

## Tableau Dashboard

Published link: https://public.tableau.com/app/profile/nkuranga.baziga.caleb/viz/Global_Disaster_Events_Analysis/Dashboard1

Four charts: Disasters by Type, Disaster Geographic Map, Disaster Events Over Time, and Model
Predictions vs Actual. Two filters: Year and Event Type.

## What I would improve with more time

- Incremental loading only adds new years and never re-checks a year that's already loaded,
  even if GDACS later revises that year's data
- `population_value` looked useful at first but GDACS's SEARCH endpoint doesn't actually
  provide it — a per-event API call could add it, at the cost of many extra requests
- The class imbalance between Orange and Red events (roughly 4 to 1) limits how well any
  model can learn to recognize Red events specifically
- The AI assistant has no memory between questions, so it can't handle follow-ups like
  "what about the lowest one instead"
- The dashboard is built from a static CSV export, so it won't auto-update when new data is
  loaded — it would need to be re-exported and republished
