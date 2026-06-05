import pandas as pd
from pathlib import Path
from sqlalchemy import text
from loguru import logger
from database.db import get_engine


STAGED_DIR = Path("data/staged")

def get_latest_file(prefix: str) -> Path:
    files = sorted(STAGED_DIR.glob(f"{prefix}_*.csv"))
    if not files:
        raise FileNotFoundError(f"No staged file found for prefix: {prefix}")
    return files[-1]


def load_prices(engine):
    path = get_latest_file("prices_clean")
    df = pd.read_csv(path)

    prices_df = df[["resource_id", "date", "value", "pct_change_1d", "rolling_avg_7d", "rolling_avg_30d", "z_score", "rolling_std_365d"]]

    prices_df.to_sql("prices", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(prices_df)} rows into prices from {path.name}")

    signals_df = df[["resource_id", "date", "z_score", "flag", "price_dev_pct"]]
    signals_df.to_sql("shortage_signals", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(signals_df)} rows into shortage_signals from {path.name}")


def load_inventory(engine):
    path = get_latest_file("inventory_clean")
    df = pd.read_csv(path)
    df.to_sql("inventory_levels", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into inventory_levels from {path.name}")

def load_production(engine):
    path = get_latest_file("production_clean")
    df = pd.read_csv(path)
    df.to_sql("production", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into production from {path.name}")

def load_headlines(engine):
    path = get_latest_file("headlines_clean")
    df = pd.read_csv(path)
    df.to_sql("news_headlines", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into news_headlines from {path.name}")


def run():
    engine = get_engine()
    logger.info("Starting database load — truncating existing data")
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE prices, shortage_signals, inventory_levels, production, news_headlines RESTART IDENTITY CASCADE"))
        conn.commit()
    load_prices(engine)
    load_inventory(engine)
    load_production(engine)
    load_headlines(engine)
    logger.info("Database load complete")



if __name__ == "__main__":
    run()

