from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class FlagHistoryEntry(BaseModel):
    date: date
    flag: str

class CommodityOverview(BaseModel):
    slug: str
    resource_id: int
    name: str
    unit: str
    latest_price: float
    price_dev_pct: float
    flag: str
    days_in_flag: Optional[int]
    flag_history: list[FlagHistoryEntry]

class HeadlineData(BaseModel):
    headline: str
    source: str
    published_at: datetime
    resource_name: str
    sentiment: float
    url: Optional[str]

class SupplyBalance(BaseModel):
    current_gap_tbpd: float
    min_gap_tbpd: float
    max_gap_tbpd: float
    latest_date: date

class OverviewMeta(BaseModel):
    last_updated: date
    data_freshness: str

class OverviewResponse(BaseModel):
    commodities: list[CommodityOverview]
    headlines: list[HeadlineData]
    supply_balance: Optional[SupplyBalance]
    meta: OverviewMeta

class PriceTrendEntry(BaseModel):
    date: date
    price: float
    risky_threshold: Optional[float]
    critical_threshold: Optional[float]

class ComparisonData(BaseModel):
    current_price: float
    avg_30d: float
    avg_1y: float
    dev_vs_30d_pct: float
    dev_vs_1y_pct: float

class InventoryData(BaseModel):
    current_level: float
    unit: str
    five_year_max: float
    fill_pct: float
    streak_direction: str
    streak_weeks: int
    latest_date: date

class ProductionTrendEntry(BaseModel):
    date: date
    volume_tbpd: float
    rolling_avg_12m: Optional[float]

class CommodityMeta(BaseModel):
    slug: str
    resource_id: int
    name: str
    unit: str
    current_flag: str
    latest_price: float

class CommodityResponse(BaseModel):
    meta: CommodityMeta
    price_trend: list[PriceTrendEntry]
    comparison: ComparisonData
    inventory: Optional[InventoryData]
    production_trend: list[ProductionTrendEntry]

