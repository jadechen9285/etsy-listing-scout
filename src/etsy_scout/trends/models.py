"""Data shapes for keyword-level trend and market data."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

# Column order of the `rankhero_search_trend` sheet in the market-research workbook.
TREND_TEMPLATE_COLUMNS = [
    "Keyword",
    "Typical monthly searches",
    "Competing listings",
    "Ad cost per click",
    "Trend",
]


class MonthlySearches(BaseModel):
    month: date  # first day of the month
    searches: int


class CountryShare(BaseModel):
    country: str
    value: int
    pct: float | None = None


class TrendSummary(BaseModel):
    """Numbers derived from a 12-month search series."""

    label: str
    change_pct: float | None = None  # last 3 months vs first 3 months
    peak_month: date | None = None
    low_month: date | None = None
    seasonality_ratio: float | None = None  # peak / low
    latest_vs_avg_pct: float | None = None  # latest month vs the 12-month average
    yoy_pct: float | None = None  # last 12 vs prior 12 months (needs 24+ months of history)


class KeywordTrend(BaseModel):
    """One keyword's demand data, as imported from a saved RankHero keyword page."""

    keyword: str
    source_url: str | None = None
    updated: date | None = None
    monthly_searches: int | None = None
    competing_listings: int | None = None  # metric card (all countries)
    competing_listings_alt: int | None = None  # figure quoted in the page summary
    cpc: float | None = None
    keyword_difficulty: int | None = None
    price_low: float | None = None
    price_high: float | None = None
    price_median: float | None = None
    price_sample_size: int | None = None
    price_bands: dict[str, float] = Field(default_factory=dict)  # band label -> % of listings
    search_by_country: list[CountryShare] = Field(default_factory=list)
    competition_by_country: list[CountryShare] = Field(default_factory=list)
    monthly: list[MonthlySearches] = Field(default_factory=list)
    related_keywords: list[str] = Field(default_factory=list)
    summary: TrendSummary | None = None


class MarketSnapshot(BaseModel):
    """Etsy's own numbers for a keyword at one point in time (from the Open API)."""

    snapshot_date: date
    keyword: str
    exclude_digital: bool
    competing_listings: int | None = None  # total active listings matching the keyword
    sample_size: int = 0  # listings used for the price stats below
    price_min: float | None = None
    price_p25: float | None = None
    price_median: float | None = None
    price_p75: float | None = None
    price_max: float | None = None
    avg_favorites: float | None = None
    price_bands: dict[str, float] = Field(default_factory=dict)
