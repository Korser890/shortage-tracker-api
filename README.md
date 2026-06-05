# shortage-tracker-api

Data pipeline and REST API for tracking global energy commodity shortages. Pulls raw data from public APIs (EIA, FRED, NewsAPI), transforms it into clean shortage signals, loads it into PostgreSQL, and serves it via FastAPI.

## Stack

- Python 3.11 · FastAPI · PostgreSQL · SQLAlchemy Core · pandas · loguru · vaderSentiment

## Setup

**1. Clone and create virtual environment**

git clone <repo-url>
cd global-shortage-tracker
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt


**2. Configure environment variables**

cp .env.example .env
Fill in your API keys and PostgreSQL credentials in `.env`.


**3. Create the database schema**

psql -U your_db_user -d your_db_name -f database/schema.sql


## Running the pipeline

python pipeline/run_pipeline.py

Fetches fresh data from all sources, transforms it, and loads it into PostgreSQL. Takes ~35 seconds on a full run.

## Starting the API

uvicorn api.main:app --reload


API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/overview` | All commodities + headlines + supply balance |
| GET | `/api/commodity/{slug}` | Detail view for a single commodity |

## Data sources

| Source | Data | Key in .env |
|--------|------|-------------|
| EIA API v2 | Crude oil + gas prices, US inventory | `EIA_API_KEY` |
| FRED API | EU TTF gas price | `FRED_API_KEY` |
| EIA International | Global production by region | `EIA_API_KEY` |
| NewsAPI | Energy headlines + sentiment | `NEWS_API_KEY` |



