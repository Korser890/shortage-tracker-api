import json
import sys
from pathlib import Path
from datetime import date

import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAW_DIR    = Path(__file__).resolve().parents[1] / "data" / "raw"
STAGED_DIR = Path(__file__).resolve().parents[1] / "data" / "staged"

INVENTORY_PATTERNS = [
    "eia_pet_wcsstus1_w_*.json",
]


def load_raw_inventory() -> pd.DataFrame:
    frames = []

    for pattern in INVENTORY_PATTERNS:
        matches = sorted(RAW_DIR.glob(pattern))
        if not matches:
            logger.warning(f"No file found for pattern: {pattern}")
            continue

        filepath = matches[-1]
        logger.info(f"Loading {filepath.name}")

        with open(filepath) as f:
            raw = json.load(f)

        rows = raw["data"]["response"]["data"]
        resource_id = raw["resource_id"]

        df = pd.DataFrame(rows)[["period", "value", "units", "area-name"]]
        df["resource_id"] = resource_id
        df = df.rename(columns={
            "period":    "date",
            "value":     "level",
            "units":     "unit",
            "area-name": "country",
        })
        df["region"] = "Americas"

        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()]

    df["level"] = pd.to_numeric(df["level"], errors="coerce")

    bad_rows = df["level"].isna().sum()
    if bad_rows > 0:
        logger.warning(f"Dropping {bad_rows} rows where level could not be cast to float")
    df = df[df["level"].notna()]

    df = df[df["date"] <= pd.Timestamp(date.today())]

    df = df.sort_values(["resource_id", "date"])
    df = df.drop_duplicates(subset=["resource_id", "date"], keep="last")

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    return df

def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["resource_id", "date"])
    df["wow_change"] = (
        df.groupby("resource_id")["level"]
        .diff()
        .round(3)
    )
    return df


def quality_checks(df: pd.DataFrame) -> None:
    assert df["date"].notna().all(),     "Null dates found after cleaning"
    assert df["level"].notna().all(),    "Null levels found after cleaning"
    assert df["unit"].notna().all(),     "Null units found after cleaning"
    assert df["region"].notna().all(),   "Null regions found after cleaning"
    assert df["country"].notna().all(),  "Null countries found after cleaning"

    assert (pd.to_datetime(df["date"]) <= pd.Timestamp(date.today())).all(), "Future-dated rows found"

    logger.info(f"Quality checks passed — {len(df)} inventory rows")

def run() -> pd.DataFrame:
    STAGED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading raw inventory data")
    df = load_raw_inventory()

    logger.info("Cleaning data")
    df = clean(df)

    logger.info("Calculating metrics")
    df = calculate_metrics(df)

    quality_checks(df)

    today = date.today().isoformat()
    outfile = STAGED_DIR / f"inventory_clean_{today}.csv"
    df.to_csv(outfile, index=False)
    logger.info(f"Saved → {outfile.name}")

    return df


if __name__ == "__main__":
    run()



