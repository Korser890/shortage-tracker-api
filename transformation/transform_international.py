import json
import sys
from pathlib import Path
from datetime import date

import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAW_DIR    = Path(__file__).resolve().parents[1] / "data" / "raw"
STAGED_DIR = Path(__file__).resolve().parents[1] / "data" / "staged"

PRODUCTION_PATTERN  = "eia_intl_world_oil_production_*.json"
OPEC_PATTERN        = "eia_intl_opec_production_*.json"
CONSUMPTION_PATTERN = "eia_intl_world_oil_consumption_*.json"

REGION_MAP = {
    "SAU": "Middle East",     "IRN": "Middle East",     "IRQ": "Middle East",
    "ARE": "Middle East",     "KWT": "Middle East",     "QAT": "Middle East",
    "OMN": "Middle East",     "YEM": "Middle East",     "BHR": "Middle East",
    "SYR": "Middle East",
    "NGA": "Africa",          "LBY": "Africa",          "DZA": "Africa",
    "AGO": "Africa",          "EGY": "Africa",          "GNQ": "Africa",
    "GAB": "Africa",          "COG": "Africa",          "SDN": "Africa",
    "SSD": "Africa",          "TCD": "Africa",          "TUN": "Africa",
    "CMR": "Africa",
    "USA": "Americas",        "CAN": "Americas",        "MEX": "Americas",
    "VEN": "Americas",        "BRA": "Americas",        "COL": "Americas",
    "ECU": "Americas",        "ARG": "Americas",        "PER": "Americas",
    "TTO": "Americas",        "GUY": "Americas",
    "RUS": "Europe & Eurasia","NOR": "Europe & Eurasia","GBR": "Europe & Eurasia",
    "AZE": "Europe & Eurasia","KAZ": "Europe & Eurasia","TKM": "Europe & Eurasia",
    "UZB": "Europe & Eurasia","DNK": "Europe & Eurasia","ROU": "Europe & Eurasia",
    "CHN": "Asia & Oceania",  "IND": "Asia & Oceania",  "IDN": "Asia & Oceania",
    "MYS": "Asia & Oceania",  "AUS": "Asia & Oceania",  "VNM": "Asia & Oceania",
    "BRN": "Asia & Oceania",
}

def load_production_countries() -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob(PRODUCTION_PATTERN))
    if not matches:
        raise FileNotFoundError(f"No file matching {PRODUCTION_PATTERN}")

    filepath = matches[-1]
    logger.info(f"Loading {filepath.name}")

    with open(filepath) as f:
        raw = json.load(f)

    resource_id = raw["resource_id"]
    type_val    = raw["type"]
    rows        = raw["data"]

    df = pd.DataFrame(rows)[["period", "countryRegionId", "countryRegionName", "countryRegionTypeId", "value"]]
    df["resource_id"] = resource_id
    df["type"]        = type_val

    logger.info(f"Loaded {len(df)} country-level production rows")
    return df

def load_opec_production() -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob(OPEC_PATTERN))
    if not matches:
        raise FileNotFoundError(f"No file matching {OPEC_PATTERN}")

    filepath = matches[-1]
    logger.info(f"Loading {filepath.name}")

    with open(filepath) as f:
        raw = json.load(f)

    resource_id = raw["resource_id"]
    type_val    = raw["type"]
    rows        = raw["data"]

    df = pd.DataFrame(rows)[["period", "value"]]
    df["resource_id"] = resource_id
    df["type"]        = type_val

    logger.info(f"Loaded {len(df)} OPEC production rows")
    return df

def load_consumption() -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob(CONSUMPTION_PATTERN))
    if not matches:
        raise FileNotFoundError(f"No file matching {CONSUMPTION_PATTERN}")

    filepath = matches[-1]
    logger.info(f"Loading {filepath.name}")

    with open(filepath) as f:
        raw = json.load(f)

    resource_id = raw["resource_id"]
    type_val    = raw["type"]
    rows        = raw["data"]

    df = pd.DataFrame(rows)[["period", "value"]]
    df["resource_id"] = resource_id
    df["type"]        = type_val

    logger.info(f"Loaded {len(df)} world consumption rows")
    return df


def clean_production_countries(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["period"] + "-01", errors="coerce")
    df = df[df["date"].notna()]

    region_rows = (df["countryRegionTypeId"] != "c").sum()
    if region_rows > 0:
        logger.info(f"Dropping {region_rows} pre-aggregated region rows (type != 'c')")
    df = df[df["countryRegionTypeId"] == "c"]

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    bad_rows = df["value"].isna().sum()
    if bad_rows > 0:
        logger.warning(f"Dropping {bad_rows} rows where value could not be cast to float")
    df = df[df["value"].notna()]

    df = df[df["date"] <= pd.Timestamp(date.today())]

    df = df.drop_duplicates(subset=["countryRegionId", "date"], keep="last")

    df["region"] = df["countryRegionId"].map(REGION_MAP).fillna("Other")

    unmapped = df[df["region"] == "Other"]["countryRegionId"].nunique()
    if unmapped > 0:
        logger.warning(f"{unmapped} country codes not in REGION_MAP — assigned 'Other'")

    return df

def aggregate_to_schema(country_df: pd.DataFrame) -> pd.DataFrame:
    resource_id = country_df["resource_id"].iloc[0]
    type_val    = country_df["type"].iloc[0]

    regional = (
        country_df.groupby(["date", "region"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "volume_tbpd"})
    )
    regional["resource_id"] = resource_id
    regional["type"]        = type_val
    regional["country"]     = regional["region"]

    world = (
        country_df.groupby("date", as_index=False)["value"]
        .sum()
        .rename(columns={"value": "volume_tbpd"})
    )
    world["resource_id"] = resource_id
    world["type"]        = type_val
    world["region"]      = "WORLD"
    world["country"]     = "WORLD"

    combined = pd.concat([regional, world], ignore_index=True)
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    logger.info(f"Aggregated production — {len(regional)} regional rows + {len(world)} world total rows")
    return combined[["resource_id", "date", "region", "volume_tbpd", "type", "country"]]

def clean_opec(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["period"] + "-01", errors="coerce")
    df = df[df["date"].notna()]

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna()]

    df = df[df["date"] <= pd.Timestamp(date.today())]
    df = df.drop_duplicates(subset=["date"], keep="last")

    df["region"]  = "OPEC"
    df["country"] = "OPEC"
    df["date"]    = df["date"].dt.strftime("%Y-%m-%d")

    return df.rename(columns={"value": "volume_tbpd"})[
        ["resource_id", "date", "region", "volume_tbpd", "type", "country"]
    ]


def clean_consumption(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["period"] + "-01", errors="coerce")
    df = df[df["date"].notna()]

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna()]

    forecast_dropped = (df["date"] > pd.Timestamp(date.today())).sum()
    df = df[df["date"] <= pd.Timestamp(date.today())]
    if forecast_dropped > 0:
        logger.info(f"Dropped {forecast_dropped} STEO forecast rows")
    df = df.drop_duplicates(subset=["date"], keep="last")

    df["volume_tbpd"] = df["value"] * 1000
    df["region"]      = "WORLD"
    df["country"]     = "WORLD"
    df["date"]        = df["date"].dt.strftime("%Y-%m-%d")

    logger.info(f"Consumption unit converted: MBPD → TBPD (×1000)")
    return df[["resource_id", "date", "region", "volume_tbpd", "type", "country"]]

def calculate_production_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["resource_id", "region", "date"]).reset_index(drop=True)

    # YoY % change — compare each month to the same month 12 periods earlier,
    # grouped per (resource_id, region) so regions don't bleed into each other
    df["yoy_pct_change"] = (
        df.groupby(["resource_id", "region"])["volume_tbpd"]
        .transform(lambda x: x.pct_change(periods=12).mul(100).round(2))
    )

    # Build date-indexed lookup series for world production and consumption
    world_prod = (
        df[(df["resource_id"] == 5) & (df["region"] == "WORLD")]
        .set_index("date")["volume_tbpd"]
    )
    world_cons = df[df["resource_id"] == 7].set_index("date")["volume_tbpd"]

    # Supply-demand gap — world production minus world consumption per month.
    # Populated only on resource_id=5 WORLD rows; NaN everywhere else.
    gap_series = (world_prod - world_cons).round(2)
    df["gap_tbpd"] = float("nan")
    prod_world_mask = (df["resource_id"] == 5) & (df["region"] == "WORLD")
    df.loc[prod_world_mask, "gap_tbpd"] = df.loc[prod_world_mask, "date"].map(gap_series)

    # OPEC share of world production — populated only on resource_id=6 rows.
    df["opec_share_pct"] = float("nan")
    opec_mask = df["resource_id"] == 6
    df.loc[opec_mask, "opec_share_pct"] = (
        df.loc[opec_mask, "volume_tbpd"]
        / df.loc[opec_mask, "date"].map(world_prod)
        * 100
    ).round(2)

    logger.info(
        f"Metrics calculated — "
        f"yoy_pct_change: {df['yoy_pct_change'].notna().sum()} rows, "
        f"gap_tbpd: {df['gap_tbpd'].notna().sum()} rows, "
        f"opec_share_pct: {df['opec_share_pct'].notna().sum()} rows"
    )

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def quality_checks(df: pd.DataFrame) -> None:
    assert df["date"].notna().all(),        "Null dates found"
    assert df["volume_tbpd"].notna().all(), "Null volumes found"
    assert (df["volume_tbpd"] >= 0).all(),  "Negative volume found"
    assert (pd.to_datetime(df["date"]) <= pd.Timestamp(date.today())).all(), "Future-dated rows found"
    assert df["resource_id"].isin([5, 6, 7]).all(), "Unexpected resource_id found"

    # gap_tbpd should be populated for every rid=5 WORLD row that has a matching consumption date
    gap_populated = df.loc[(df["resource_id"] == 5) & (df["region"] == "WORLD"), "gap_tbpd"].notna().sum()
    opec_populated = df.loc[df["resource_id"] == 6, "opec_share_pct"].notna().sum()
    logger.info(f"gap_tbpd populated on {gap_populated} rows, opec_share_pct on {opec_populated} rows")

    for rid, group in df.groupby("resource_id"):
        logger.info(
            f"resource_id={rid} — {len(group)} rows — "
            f"{group['date'].min()} to {group['date'].max()}"
        )

    logger.info("Quality checks passed")



def run() -> pd.DataFrame:
    STAGED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading raw international production/consumption data")
    prod_countries_df = load_production_countries()
    opec_df           = load_opec_production()
    consumption_df    = load_consumption()

    logger.info("Cleaning data")
    prod_countries_df = clean_production_countries(prod_countries_df)
    opec_df           = clean_opec(opec_df)
    consumption_df    = clean_consumption(consumption_df)

    logger.info("Aggregating production to regional and world totals")
    production_df = aggregate_to_schema(prod_countries_df)

    logger.info("Combining all series")
    df = pd.concat([production_df, opec_df, consumption_df], ignore_index=True)

    logger.info("Calculating derived metrics")
    df = calculate_production_metrics(df)

    quality_checks(df)

    today   = date.today().isoformat()
    outfile = STAGED_DIR / f"production_clean_{today}.csv"
    df.to_csv(outfile, index=False)
    logger.info(f"Saved → {outfile.name} ({len(df)} rows)")

    return df


if __name__ == "__main__":
    run()

