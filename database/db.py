import os
from sqlalchemy import create_engine, text
from loguru import logger

def _get_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    engine = create_engine(_get_url())
    return engine

def test_connection():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        logger.info(f"DB connection successful: {result.fetchone()}")

if __name__ == "__main__":
    test_connection()
