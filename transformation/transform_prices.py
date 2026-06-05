import json
import sys
from pathlib import Path
from datetime import date

import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


RAW_DIR    = Path(__file__).resolve().parents[1] / "data" / "raw"
STAGED_DIR = Path(__file__).resolve().parents[1] / "data" / "staged"

EIA_PRICE_PATTERNS = [
    "eia_pet_rbrte_d_*.json",
    "eia_pet_rwtc_d_*.json",
    "eia_ng_rngwhhd_d_*.json",
]

FRED_PRICE_PATTERNS = [
    "fred_pngaseuusdm_*.json",
]

MAX_FILL_DAYS = 3


def load_eia_prices() -> pd.DataFrame:
    frames = []

    for pattern in EIA_PRICE_PATTERNS:
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

        df = pd.DataFrame(rows)[["period", "value"]]
        df["resource_id"] = resource_id
        df = df.rename(columns={"period": "date"})

        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_fred_prices() -> pd.DataFrame:
    frames = []

    for pattern in FRED_PRICE_PATTERNS:
        matches = sorted(RAW_DIR.glob(pattern))
        if not matches:
            logger.warning(f"No file found for pattern: {pattern}")
            continue

        filepath = matches[-1]
        logger.info(f"Loading {filepath.name}")

        with open(filepath) as f:
            raw = json.load(f)

        rows = raw["data"]["observations"]
        resource_id = raw["resource_id"]

        df = pd.DataFrame(rows)[["date", "value"]]
        df["resource_id"] = resource_id

        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()



def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()]

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    bad_rows = df["value"].isna().sum()
    if bad_rows > 0:
        logger.warning(f"Dropping {bad_rows} rows where value could not be cast to float")
    df = df[df["value"].notna()]

    df = df[df["date"] <= pd.Timestamp(date.today())]

    df = df.sort_values(["resource_id", "date"])
    df = df.drop_duplicates(subset=["resource_id", "date"], keep="last")

    df = (
        df.set_index("date")
        .groupby("resource_id", group_keys=False)
        .apply(lambda g: g["value"].resample("D").interpolate(method="linear", limit=MAX_FILL_DAYS).to_frame().assign(resource_id=g.name))
        .reset_index()
    )

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["value"])

    return df


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["resource_id", "date"])

    df["pct_change_1d"] = (
        df.groupby("resource_id")["value"]
        .pct_change()
        .mul(100)
        .round(4)
    )

    df["rolling_avg_7d"] = (
        df.groupby("resource_id")["value"]
        .transform(lambda x: x.rolling(7, min_periods=1).mean().round(4))
    )

    df["rolling_avg_30d"] = (
        df.groupby("resource_id")["value"]
        .transform(lambda x: x.rolling(30, min_periods=1).mean().round(4))
    )

    df["rolling_mean_365d"] = (
        df.groupby("resource_id")["value"]
        .transform(lambda x: x.rolling(365, min_periods=30).mean())
    )

    df["rolling_std_365d"] = (
        df.groupby("resource_id")["value"]
        .transform(lambda x: x.rolling(365, min_periods=30).std())
    )

    df["z_score"] = (
        (df["value"] - df["rolling_mean_365d"]) / df["rolling_std_365d"]
    ).round(4)

    df["rolling_std_365d"] = df["rolling_std_365d"].round(4)
    df = df.drop(columns=["rolling_mean_365d"])


    return df


def generate_shortage_flags(df: pd.DataFrame) -> pd.DataFrame:
    mean_12m = (
        df.groupby("resource_id")["value"]
        .transform(lambda x: x.rolling(365, min_periods=30).mean())
    )

    df["price_dev_pct"] = ((df["value"] - mean_12m) / mean_12m * 100).round(4)

    def assign_flag(row):
        z = row["z_score"]
        dev = row["price_dev_pct"]

        if pd.isna(z) or pd.isna(dev):
            return "NORMAL"
        if z > 2.0 or dev > 30.0:
            return "CRITICAL"
        if z >= 1.0 or dev >= 15.0:
            return "RISKY"
        return "NORMAL"

    df["flag"] = df.apply(assign_flag, axis=1)

    return df


def quality_checks(df: pd.DataFrame) -> None:
    assert df["date"].notna().all(), "Null dates found after cleaning"
    assert df["value"].notna().all(), "Null values found after cleaning"
    assert (pd.to_datetime(df["date"]) <= pd.Timestamp(date.today())).all(), "Future-dated rows found"
    assert df["flag"].isin(["NORMAL", "RISKY", "CRITICAL"]).all(), "Invalid flag value found"

    z_extremes = df["z_score"].dropna()
    extreme_count = (z_extremes.abs() > 5).sum()
    if extreme_count > 0:
        logger.warning(f"{extreme_count} rows with z-score outside ±5 — possible outliers")

    logger.info("Quality checks passed")


def run() -> pd.DataFrame:
    STAGED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading raw price data")
    eia_df  = load_eia_prices()
    fred_df = load_fred_prices()
    df = pd.concat([eia_df, fred_df], ignore_index=True)

    logger.info("Cleaning data")
    df = clean(df)

    logger.info("Calculating metrics")
    df = calculate_metrics(df)

    logger.info("Generating shortage flags")
    df = generate_shortage_flags(df)

    quality_checks(df)

    today = date.today().isoformat()
    outfile = STAGED_DIR / f"prices_clean_{today}.csv"
    df.to_csv(outfile, index=False)
    logger.info(f"Saved → {outfile.name}")

    return df


if __name__ == "__main__":
    run()



