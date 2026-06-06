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

def seed_resources(engine):
    rows = [
        (1, 'Brent Crude Oil',       'Energy', 'USD/barrel', 'EIA',  'daily',   'Global oil benchmark price - North Sea'),
        (2, 'WTI Crude Oil',         'Energy', 'USD/barrel', 'EIA',  'daily',   'US oil benchmark price - Cushing Oklahoma'),
        (3, 'Henry Hub Natural Gas', 'Energy', 'USD/MMBtu',  'EIA',  'daily',   'US natural gas benchmark price'),
        (4, 'EU Natural Gas (TTF)',  'Energy', 'USD/MMBtu',  'FRED', 'monthly', 'European natural gas benchmark price'),
        (5, 'World Oil Production',  'Energy', 'TBPD',       'EIA',  'monthly', 'Total world crude oil production'),
        (6, 'OPEC Production',       'Energy', 'TBPD',       'EIA',  'monthly', 'OPEC member countries crude oil production'),
        (7, 'World Oil Consumption', 'Energy', 'TBPD',       'EIA',  'monthly', 'Total world petroleum consumption'),
    ]
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO resources (resource_id, name, category, unit, source, frequency, description)
            VALUES (:id, :name, :category, :unit, :source, :frequency, :description)
            ON CONFLICT (resource_id) DO NOTHING
        """), [dict(id=r[0], name=r[1], category=r[2], unit=r[3], source=r[4], frequency=r[5], description=r[6]) for r in rows])
        conn.commit()
    logger.info("Resources seeded (7 rows, skipped if already present)")


def run():
    engine = get_engine()
    seed_resources(engine)
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

