import json
import sys
import time
from datetime import date
from pathlib import Path

import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.config import EIA_API_KEY


# (activity_id, product_id, country_region_id, resource_id, label, type_val)
# country_region_id = None means fetch all countries (no region filter)
EIA_INTL_SERIES = [
    ("1", "53", None,   5, "World Oil Production",  "WORLD"),
    ("1", "53", "OPEC", 6, "OPEC Production",        "OPEC"),
]



RAW_DIR        = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE_URL       = "https://api.eia.gov/v2/international/data/"
STEO_BASE_URL  = "https://api.eia.gov/v2/steo/data/"

# World consumption via STEO — EIA International has no reliable country-level consumption
# PATC_WORLD = world total petroleum and other liquids consumption in MBPD
# Transformation will convert MBPD → TBPD (×1000) to match production units
STEO_SERIES = [
    ("PATC_WORLD", 7, "World Oil Consumption", "WORLD"),
]

def fetch_international(
    activity_id: str,
    product_id: str,
    country_region_id: str | None,
    start: str,
    end: str,
    retries: int = 3,
) -> list:
    all_rows = []
    offset = 0
    page_size = 5000

    while True:
        params = {
            "api_key": EIA_API_KEY,
            "frequency": "monthly",
            "data[0]": "value",
            "facets[activityId][]": activity_id,
            "facets[productId][]": product_id,
            "start": start,
            "end": end,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": page_size,
            "offset": offset,
        }

        if country_region_id is not None:
            params["facets[countryRegionId][]"] = country_region_id

        for attempt in range(1, retries + 1):
            try:
                logger.info(
                    f"Fetching activity={activity_id} region={country_region_id or 'ALL'} "
                    f"offset={offset} (attempt {attempt}/{retries})"
                )
                response = requests.get(BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("response", {}).get("data", [])
                break
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
        else:
            raise RuntimeError(
                f"Failed to fetch activity={activity_id} region={country_region_id} "
                f"offset={offset} after {retries} attempts"
            )

        all_rows.extend(rows)
        logger.info(f"Page fetched — {len(rows)} rows, total so far: {len(all_rows)}")

        if len(rows) < page_size:
            break
        offset += page_size

    logger.info(f"activity={activity_id} region={country_region_id or 'ALL'} — {len(all_rows)} total rows fetched")
    return all_rows



def fetch_steo(series_id: str, start: str, end: str, retries: int = 3) -> list:
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": series_id,
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching STEO {series_id} (attempt {attempt}/{retries})")
            response = requests.get(STEO_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("response", {}).get("data", [])
            logger.info(f"STEO {series_id} — {len(rows)} rows received")
            return rows
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

    raise RuntimeError(f"Failed to fetch STEO {series_id} after {retries} attempts")


def run(start: str = "2015-01", end: str = None) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    if end is None:
        end = date.today().strftime("%Y-%m")

    logger.info(f"EIA International ingestion — range: {start} to {end}")

    for activity_id, product_id, country_region_id, resource_id, label, type_val in EIA_INTL_SERIES:
        try:
            rows = fetch_international(activity_id, product_id, country_region_id, start, end)
        except RuntimeError as e:
            logger.error(str(e))
            continue

        safe_label = label.lower().replace(" ", "_")
        filename = RAW_DIR / f"eia_intl_{safe_label}_{today}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "label": label,
                    "resource_id": resource_id,
                    "type": type_val,
                    "activity_id": activity_id,
                    "product_id": product_id,
                    "country_region_id": country_region_id,
                    "fetched_at": today,
                    "data": rows,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved → {filename.name} ({len(rows)} rows)")

    for series_id, resource_id, label, type_val in STEO_SERIES:
        try:
            rows = fetch_steo(series_id, start, end)
        except RuntimeError as e:
            logger.error(str(e))
            continue

        safe_label = label.lower().replace(" ", "_")
        filename = RAW_DIR / f"eia_intl_{safe_label}_{today}.json"

        with open(filename, "w") as f:
            json.dump(
                {
                    "label": label,
                    "resource_id": resource_id,
                    "type": type_val,
                    "series_id": series_id,
                    "source": "STEO",
                    "unit": "MBPD",
                    "fetched_at": today,
                    "data": rows,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved → {filename.name} ({len(rows)} rows)")

    logger.info("EIA International ingestion complete")


if __name__ == "__main__":
    run()
