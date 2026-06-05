import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.config import FRED_API_KEY

FRED_SERIES = [
    ("CPIENGSL",     None, "Energy CPI",            "monthly"),
    ("PNGASEUUSDM",  4,    "EU Natural Gas (TTF)",   "monthly"),
]

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_LOOKBACK_DAYS = 365 * 5  # 5 years of history on first run

def fetch_series(series_id: str, start: str, end: str, retries: int = 3) -> dict:
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
        "sort_order": "asc",
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching {series_id} (attempt {attempt}/{retries})")
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            payload = response.json()
            rows = payload.get("observations", [])

            if not rows:
                logger.warning(f"{series_id} — empty response for range {start} to {end}")
            else:
                logger.info(f"{series_id} — {len(rows)} rows received")

            return payload
        except requests.exceptions.HTTPError as e:
            logger.error(f"{series_id} — HTTP {response.status_code}: {e}")
        except requests.exceptions.ConnectionError:
            logger.error(f"{series_id} — connection error on attempt {attempt}")
        except requests.exceptions.Timeout:
            logger.error(f"{series_id} — request timed out on attempt {attempt}")
        except requests.exceptions.RequestException as e:
            logger.error(f"{series_id} — unexpected error: {e}")

        if attempt < retries:
            wait = 2 ** attempt
            logger.info(f"Retrying in {wait}s ...")
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {series_id} after {retries} attempts")

def run(start: str = None, end: str = None) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    if end is None:
        end = today
    if start is None:
        start = (date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).isoformat()

    logger.info(f"FRED energy ingestion — range: {start} to {end}")

    for series_id, resource_id, label, frequency in FRED_SERIES:
        try:
            payload = fetch_series(series_id, start, end)
        except RuntimeError as e:
            logger.error(str(e))
            continue

        safe_series = series_id.lower()
        filename = RAW_DIR / f"fred_{safe_series}_{today}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "series_id": series_id,
                    "resource_id": resource_id,
                    "label": label,
                    "frequency": frequency,
                    "fetched_at": today,
                    "data": payload,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved → {filename.name}")

    logger.info("FRED energy ingestion complete")

if __name__ == "__main__":
    run()
