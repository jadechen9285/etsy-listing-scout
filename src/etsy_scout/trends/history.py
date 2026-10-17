"""Local history so repeated runs build trend lines over time.

Two CSV files live in the history folder (default `data/`, git-ignored):
- keyword_history.csv  one row per (date, keyword, source) snapshot
- monthly_searches.csv RankHero monthly search series, merged across imports, so after
                       a year of imports there are 24+ months and a true year-over-year
                       trend can be computed
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import KeywordTrend, MarketSnapshot, MonthlySearches

DEFAULT_DIR = Path("data")
HISTORY_FILE = "keyword_history.csv"
MONTHLY_FILE = "monthly_searches.csv"
HISTORY_COLUMNS = [
    "snapshot_date",
    "keyword",
    "source",
    "monthly_searches",
    "competing_listings",
    "cpc",
    "keyword_difficulty",
    "trend",
    "sample_size",
    "price_min",
    "price_p25",
    "price_median",
    "price_p75",
    "price_max",
    "avg_favorites",
]


def snapshot_record(s: MarketSnapshot) -> dict:
    return {
        "snapshot_date": s.snapshot_date.isoformat(),
        "keyword": s.keyword,
        "source": "etsy_api" + ("" if s.exclude_digital else "_incl_digital"),
        "competing_listings": s.competing_listings,
        "sample_size": s.sample_size,
        "price_min": s.price_min,
        "price_p25": s.price_p25,
        "price_median": s.price_median,
        "price_p75": s.price_p75,
        "price_max": s.price_max,
        "avg_favorites": s.avg_favorites,
    }


def trend_record(t: KeywordTrend) -> dict:
    return {
        "snapshot_date": t.updated.isoformat() if t.updated else None,
        "keyword": t.keyword,
        "source": "rankhero",
        "monthly_searches": t.monthly_searches,
        "competing_listings": t.competing_listings,
        "cpc": t.cpc,
        "keyword_difficulty": t.keyword_difficulty,
        "trend": t.summary.label if t.summary else None,
        "sample_size": t.price_sample_size,
        "price_min": t.price_low,
        "price_median": t.price_median,
        "price_max": t.price_high,
    }


def _upsert(path: Path, new: pd.DataFrame, keys: list[str], columns: list[str]) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns)
    frames = [f for f in (old, new) if not f.empty]
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
    merged["_kw"] = merged["keyword"].str.lower()
    merged = merged.drop_duplicates(
        subset=["_kw", *[k for k in keys if k != "keyword"]], keep="last"
    )
    merged = merged.drop(columns="_kw").sort_values(keys).reindex(columns=columns)
    merged.to_csv(path, index=False)
    return merged


def append_history(records: list[dict], folder: Path = DEFAULT_DIR) -> pd.DataFrame:
    new = pd.DataFrame(records, columns=HISTORY_COLUMNS)
    return _upsert(
        folder / HISTORY_FILE, new, ["keyword", "source", "snapshot_date"], HISTORY_COLUMNS
    )


def merge_monthly(trends: list[KeywordTrend], folder: Path = DEFAULT_DIR) -> pd.DataFrame:
    rows = [
        {"keyword": t.keyword, "month": m.month.isoformat(), "searches": m.searches}
        for t in trends
        for m in t.monthly
    ]
    cols = ["keyword", "month", "searches"]
    return _upsert(folder / MONTHLY_FILE, pd.DataFrame(rows, columns=cols), cols[:2], cols)


def load_history(folder: Path = DEFAULT_DIR) -> pd.DataFrame:
    path = folder / HISTORY_FILE
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=HISTORY_COLUMNS)


def monthly_series(keyword: str, folder: Path = DEFAULT_DIR) -> list[MonthlySearches]:
    """Full stored monthly series for a keyword (may exceed the 12 months on one page)."""
    path = folder / MONTHLY_FILE
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df = df[df["keyword"].str.lower() == keyword.lower()].sort_values("month")
    return [
        MonthlySearches(month=pd.Timestamp(r.month).date(), searches=int(r.searches))
        for r in df.itertuples()
    ]
