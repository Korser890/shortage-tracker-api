import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.config import NEWS_API_KEY

COMMODITIES = [
    (1, "brent crude oil",                         "brent"),
    (2, "WTI crude oil OR West Texas Intermediate", "wti"),
    (3, "Henry Hub natural gas",                    "henry-hub"),
    (4, "TTF gas OR European natural gas",          "ttf"),
]

RAW_DIR      = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE_URL     = "https://newsapi.org/v2/everything"
LOOKBACK_DAYS = 30
PAGE_SIZE     = 20


def fetch_headlines(query: str, from_date: str, to_date: str, retries: int = 3) -> dict:
    params = {
        "q":        query,
        "from":     from_date,
        "to":       to_date,
        "language": "en",
        "sortBy":   "publishedAt",
        "pageSize": PAGE_SIZE,
        "apiKey":   NEWS_API_KEY,
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching headlines for '{query}' (attempt {attempt}/{retries})")
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            payload = response.json()
            articles = payload.get("articles", [])

            if not articles:
                logger.warning(f"No articles returned for query: '{query}'")
            else:
                logger.info(f"'{query}' — {len(articles)} articles received")

            return payload
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP {response.status_code}: {e}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error on attempt {attempt}")
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out on attempt {attempt}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected error: {e}")

        if attempt < retries:
            wait = 2 ** attempt
            logger.info(f"Retrying in {wait}s ...")
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch headlines for '{query}' after {retries} attempts")

def run() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    today     = date.today().isoformat()
    from_date = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    logger.info(f"NewsAPI ingestion — range: {from_date} to {today}")

    for resource_id, query, slug in COMMODITIES:
        try:
            payload = fetch_headlines(query, from_date, today)
        except RuntimeError as e:
            logger.error(str(e))
            continue

        filename = RAW_DIR / f"newsapi_{slug}_{today}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "resource_id": resource_id,
                    "query":       query,
                    "slug":        slug,
                    "from_date":   from_date,
                    "to_date":     today,
                    "fetched_at":  today,
                    "data":        payload,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved → {filename.name}")
        time.sleep(1)

    logger.info("NewsAPI ingestion complete")


if __name__ == "__main__":
    run()
