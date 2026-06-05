import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.config import EIA_API_KEY

# (series_id, resource_id, human label) — matches resources seed data
EIA_SERIES = [
    ("PET.RBRTE.D",  1, "Brent Crude Oil"),
    ("PET.RWTC.D",   2, "WTI Crude Oil"),
    ("NG.RNGWHHD.D", 3, "Henry Hub Natural Gas"),
]

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE_URL = "https://api.eia.gov/v2/seriesid/{series_id}"
DEFAULT_LOOKBACK_DAYS = 365 * 5  # 5 years of history on first run


def fetch_series(series_id: str, start: str, end: str, retries: int = 3) -> dict:
    url = BASE_URL.format(series_id=series_id)
    params = {
        "api_key": EIA_API_KEY,
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching {series_id} (attempt {attempt}/{retries})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            payload = response.json()
            rows = payload.get("response", {}).get("data", [])

            if not rows:
                logger.warning(f"{series_id} — API returned empty data for range {start} to {end}")
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
            logger.error(f"{series_id} — unexpected request error: {e}")

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

    logger.info(f"EIA price ingestion — range: {start} to {end}")

    for series_id, resource_id, label in EIA_SERIES:
        try:
            payload = fetch_series(series_id, start, end)
        except RuntimeError as e:
            logger.error(str(e))
            continue

        safe_series = series_id.replace(".", "_").lower()
        filename = RAW_DIR / f"eia_{safe_series}_{today}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "series_id": series_id,
                    "resource_id": resource_id,
                    "label": label,
                    "fetched_at": today,
                    "data": payload,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved → {filename.name}")

    logger.info("EIA price ingestion complete")


if __name__ == "__main__":
    run()
