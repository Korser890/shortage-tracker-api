import json
import sys
from pathlib import Path
from datetime import date

import pandas as pd
from loguru import logger
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAW_DIR    = Path(__file__).resolve().parents[1] / "data" / "raw"
STAGED_DIR = Path(__file__).resolve().parents[1] / "data" / "staged"

SLUGS = ["brent", "wti", "henry-hub", "ttf"]


def load_raw_headlines() -> pd.DataFrame:
    frames = []

    for slug in SLUGS:
        matches = sorted(RAW_DIR.glob(f"newsapi_{slug}_*.json"))
        if not matches:
            logger.warning(f"No file found for slug: {slug}")
            continue

        filepath = matches[-1]
        logger.info(f"Loading {filepath.name}")

        with open(filepath) as f:
            raw = json.load(f)

        resource_id = raw["resource_id"]
        articles    = raw["data"].get("articles", [])

        if not articles:
            logger.warning(f"{slug} — no articles in file")
            continue

        rows = []
        for article in articles:
            rows.append({
                "resource_id":  resource_id,
                "headline":     article.get("title", ""),
                "source":       article.get("source", {}).get("name", ""),
                "published_at": article.get("publishedAt", ""),
                "url":          article.get("url", None),
            })

        frames.append(pd.DataFrame(rows))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["headline"].notna() & (df["headline"] != "")]
    df = df[df["headline"] != "[Removed]"]

    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df = df[df["published_at"].notna()]

    df["date"] = df["published_at"].dt.date.astype(str)

    df = df.drop_duplicates(subset=["headline"])

    df = df.sort_values(["resource_id", "published_at"])

    return df


def apply_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    sia = SentimentIntensityAnalyzer()
    df["sentiment"] = df["headline"].apply(
        lambda h: round(sia.polarity_scores(h)["compound"], 4)
    )
    return df


def quality_checks(df: pd.DataFrame) -> None:
    assert df["headline"].notna().all(),     "Null headlines found"
    assert df["published_at"].notna().all(), "Null published_at found"
    assert df["sentiment"].between(-1, 1).all(), "Sentiment out of range"
    logger.info(f"Quality checks passed — {len(df)} headline rows")


def run() -> pd.DataFrame:
    STAGED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading raw headline data")
    df = load_raw_headlines()

    if df.empty:
        logger.warning("No headlines loaded — skipping transformation")
        return df

    logger.info("Cleaning data")
    df = clean(df)

    logger.info("Applying VADER sentiment")
    df = apply_sentiment(df)

    quality_checks(df)

    today   = date.today().isoformat()
    outfile = STAGED_DIR / f"headlines_clean_{today}.csv"
    df.to_csv(outfile, index=False)
    logger.info(f"Saved → {outfile.name}")

    return df


if __name__ == "__main__":
    run()
