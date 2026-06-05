from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from api.db import get_engine
from api.models import (
    CommodityResponse, CommodityMeta, PriceTrendEntry,
    ComparisonData, InventoryData, ProductionTrendEntry,
)
from api.routers.overview import SLUG_MAP


def get_price_trend(conn, resource_id: int) -> list[PriceTrendEntry]:
    q = text("""
        SELECT p.date, p.value AS price, p.rolling_std_365d, ss.price_dev_pct
        FROM prices p
        JOIN shortage_signals ss ON ss.resource_id = p.resource_id AND ss.date = p.date
        WHERE p.resource_id = :rid
        AND p.date >= CURRENT_DATE - INTERVAL '12 months'
        ORDER BY p.date ASC
    """)
    rows = conn.execute(q, {"rid": resource_id}).fetchall()

    entries = []
    for row in rows:
        if row.rolling_std_365d is not None:
            rolling_mean = row.price / (1 + row.price_dev_pct / 100)
            risky    = round(rolling_mean + row.rolling_std_365d,     4)
            critical = round(rolling_mean + 2 * row.rolling_std_365d, 4)
        else:
            risky = critical = None

        entries.append(PriceTrendEntry(
            date=row.date,
            price=row.price,
            risky_threshold=risky,
            critical_threshold=critical,
        ))
    return entries


def get_comparison(conn, resource_id: int) -> ComparisonData:
    q = text("""
        SELECT DISTINCT ON (p.resource_id)
            p.value AS current_price,
            p.rolling_avg_30d AS avg_30d,
            ss.price_dev_pct
        FROM prices p
        JOIN shortage_signals ss ON ss.resource_id = p.resource_id AND ss.date = p.date
        WHERE p.resource_id = :rid
        ORDER BY p.resource_id, p.date DESC
    """)
    row = conn.execute(q, {"rid": resource_id}).fetchone()

    avg_1y        = row.current_price / (1 + row.price_dev_pct / 100)
    dev_vs_30d    = (row.current_price - row.avg_30d) / row.avg_30d * 100

    return ComparisonData(
        current_price=round(row.current_price, 4),
        avg_30d=round(row.avg_30d, 4),
        avg_1y=round(avg_1y, 4),
        dev_vs_30d_pct=round(dev_vs_30d, 2),
        dev_vs_1y_pct=round(row.price_dev_pct, 2),
    )


def get_inventory(conn, resource_id: int) -> InventoryData | None:
    if resource_id in (3, 4):
        return None

    recent_q = text("""
        SELECT level, unit, date, wow_change
        FROM inventory_levels
        WHERE resource_id = 2
        ORDER BY date DESC
        LIMIT 52
    """)
    rows = conn.execute(recent_q).fetchall()
    if not rows:
        return None

    latest = rows[0]

    max_q = text("""
        SELECT MAX(level) AS five_year_max
        FROM inventory_levels
        WHERE resource_id = 2
        AND date >= CURRENT_DATE - INTERVAL '5 years'
    """)
    five_year_max = conn.execute(max_q).fetchone().five_year_max
    fill_pct = round(latest.level / five_year_max * 100, 1)

    streak_direction = "flat"
    streak_weeks = 0
    for row in rows:
        if row.wow_change is None:
            break
        direction = "declining" if row.wow_change < 0 else "building"
        if streak_weeks == 0:
            streak_direction = direction
            streak_weeks = 1
        elif direction == streak_direction:
            streak_weeks += 1
        else:
            break

    return InventoryData(
        current_level=latest.level,
        unit=latest.unit,
        five_year_max=five_year_max,
        fill_pct=fill_pct,
        streak_direction=streak_direction,
        streak_weeks=streak_weeks,
        latest_date=latest.date,
    )


def get_production_trend(conn) -> list[ProductionTrendEntry]:
    q = text("""
        SELECT date, volume_tbpd
        FROM production
        WHERE resource_id = 5
        AND region = 'WORLD'
        AND date >= CURRENT_DATE - INTERVAL '5 years'
        ORDER BY date ASC
    """)
    rows = conn.execute(q).fetchall()

    volumes = [row.volume_tbpd for row in rows]
    entries = []
    for i, row in enumerate(rows):
        if i >= 11:
            rolling_avg = round(sum(volumes[i - 11:i + 1]) / 12, 2)
        else:
            rolling_avg = None
        entries.append(ProductionTrendEntry(
            date=row.date,
            volume_tbpd=row.volume_tbpd,
            rolling_avg_12m=rolling_avg,
        ))
    return entries


router = APIRouter()

@router.get("/commodity/{slug}", response_model=CommodityResponse)
def get_commodity(slug: str):
    if slug not in SLUG_MAP:
        raise HTTPException(status_code=404, detail=f"Commodity slug '{slug}' not found")

    info = SLUG_MAP[slug]
    rid  = info["resource_id"]

    engine = get_engine()
    with engine.connect() as conn:
        meta_q = text("""
            SELECT DISTINCT ON (ss.resource_id)
                ss.flag AS current_flag,
                p.value AS latest_price
            FROM shortage_signals ss
            JOIN prices p ON p.resource_id = ss.resource_id AND p.date = ss.date
            WHERE ss.resource_id = :rid
            ORDER BY ss.resource_id, ss.date DESC
        """)
        meta_row = conn.execute(meta_q, {"rid": rid}).fetchone()

        meta = CommodityMeta(
            slug=slug,
            resource_id=rid,
            name=info["name"],
            unit=info["unit"],
            current_flag=meta_row.current_flag,
            latest_price=meta_row.latest_price,
        )

        price_trend      = get_price_trend(conn, rid)
        comparison       = get_comparison(conn, rid)
        inventory        = get_inventory(conn, rid)
        production_trend = get_production_trend(conn)

    return CommodityResponse(
        meta=meta,
        price_trend=price_trend,
        comparison=comparison,
        inventory=inventory,
        production_trend=production_trend,
    )


