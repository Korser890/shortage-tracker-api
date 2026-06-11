from fastapi import APIRouter
from sqlalchemy import text
from datetime import date
from api.db import get_engine
from api.models import (
    OverviewResponse, CommodityOverview, FlagHistoryEntry,
    HeadlineData, SupplyBalance, OverviewMeta,
)


SLUG_MAP = {
    "brent-crude": {"resource_id": 1, "name": "Brent Crude Oil",      "unit": "USD/barrel"},
    "wti-crude":   {"resource_id": 2, "name": "WTI Crude Oil",         "unit": "USD/barrel"},
    "henry-hub":   {"resource_id": 3, "name": "Henry Hub Natural Gas", "unit": "USD/MMBtu"},
    "ttf-gas":     {"resource_id": 4, "name": "EU Natural Gas (TTF)",  "unit": "USD/MMBtu"},
}

ORDERED_SLUGS = ["brent-crude", "wti-crude", "henry-hub", "ttf-gas"]


def get_commodities(conn) -> list[CommodityOverview]:
    latest_q = text("""
        SELECT DISTINCT ON (ss.resource_id)
            ss.resource_id,
            ss.flag,
            ss.price_dev_pct,
            p.value AS latest_price
        FROM shortage_signals ss
        JOIN prices p ON p.resource_id = ss.resource_id AND p.date = ss.date
        WHERE ss.resource_id IN (1, 2, 3, 4)
        ORDER BY ss.resource_id, ss.date DESC
    """)
    latest_rows = {row.resource_id: row for row in conn.execute(latest_q)}

    history_q = text("""
        SELECT resource_id, date, flag
        FROM (
            SELECT resource_id, date, flag,
                   ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY date DESC) AS rn
            FROM shortage_signals
            WHERE resource_id IN (1, 2, 3, 4)
        ) ranked
        WHERE rn <= 90
        ORDER BY resource_id, date ASC
    """)

    history_map: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    for row in conn.execute(history_q):
        history_map[row.resource_id].append(row)

    commodities = []
    for slug in ORDERED_SLUGS:
        info = SLUG_MAP[slug]
        rid = info["resource_id"]
        latest = latest_rows[rid]
        history = history_map[rid]

        current_flag = latest.flag
        streak = 0
        for entry in reversed(history):
            if entry.flag == current_flag:
                streak += 1
            else:
                break
        days_in_flag = streak if streak >= 2 else None

        commodities.append(CommodityOverview(
            slug=slug,
            resource_id=rid,
            name=info["name"],
            unit=info["unit"],
            latest_price=latest.latest_price,
            price_dev_pct=latest.price_dev_pct,
            flag=current_flag,
            days_in_flag=days_in_flag,
            flag_history=[FlagHistoryEntry(date=e.date, flag=e.flag) for e in history],
        ))

    return commodities


def get_headlines(conn, commodities: list[CommodityOverview]) -> list[HeadlineData]:
    rid_to_name = {c.resource_id: c.name for c in commodities}

    q = text("""
        SELECT headline, source, published_at, sentiment, resource_id, url
        FROM (
            SELECT DISTINCT ON (headline)
                headline, source, published_at, sentiment, resource_id, url
            FROM news_headlines
            WHERE resource_id IN (1, 2, 3, 4)
            ORDER BY headline, published_at DESC
        ) deduped
        ORDER BY published_at DESC
        LIMIT 10
    """)
    rows = conn.execute(q).fetchall()

    return [
        HeadlineData(
            headline=row.headline,
            source=row.source,
            published_at=row.published_at,
            resource_name=rid_to_name.get(row.resource_id, "Unknown"),
            sentiment=row.sentiment,
            url=row.url,
        )
        for row in rows
    ]



def get_supply_balance(conn) -> SupplyBalance | None:
    q = text("""
        SELECT
            (SELECT gap_tbpd FROM production WHERE resource_id = 5 AND gap_tbpd IS NOT NULL ORDER BY date DESC LIMIT 1) AS current_gap,
            (SELECT date    FROM production WHERE resource_id = 5 AND gap_tbpd IS NOT NULL ORDER BY date DESC LIMIT 1) AS latest_date,
            MIN(gap_tbpd) AS min_gap,
            MAX(gap_tbpd) AS max_gap
        FROM production
        WHERE resource_id = 5
    """)
    row = conn.execute(q).fetchone()
    if row is None or row.current_gap is None:
        return None

    return SupplyBalance(
        current_gap_tbpd=row.current_gap,
        min_gap_tbpd=row.min_gap,
        max_gap_tbpd=row.max_gap,
        latest_date=row.latest_date,
    )


def get_meta(conn) -> OverviewMeta:
    row = conn.execute(text("SELECT MAX(date) AS last_updated FROM prices")).fetchone()
    last_updated = row.last_updated

    delta = (date.today() - last_updated).days
    if delta == 0:
        freshness = "fresh"
    elif delta <= 3:
        freshness = "lagging"
    else:
        freshness = "stale"

    return OverviewMeta(last_updated=last_updated, data_freshness=freshness)


router = APIRouter()

@router.get("/overview", response_model=OverviewResponse)
def get_overview():
    engine = get_engine()
    with engine.connect() as conn:
        commodities    = get_commodities(conn)
        headlines      = get_headlines(conn, commodities)
        supply_balance = get_supply_balance(conn)
        meta           = get_meta(conn)

    return OverviewResponse(
        commodities=commodities,
        headlines=headlines,
        supply_balance=supply_balance,
        meta=meta,
    )

