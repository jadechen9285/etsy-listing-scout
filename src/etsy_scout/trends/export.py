"""Build the trend workbook: sheet-2 summary plus detail sheets."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

from .models import TREND_TEMPLATE_COLUMNS, KeywordTrend, MarketSnapshot

SUMMARY_SHEET = "rankhero_search_trend"


def trend_summary_frame(trends: list[KeywordTrend]) -> pd.DataFrame:
    rows = []
    for t in trends:
        s = t.summary
        rows.append(
            {
                "Keyword": t.keyword,
                "Typical monthly searches": t.monthly_searches,
                "Competing listings": t.competing_listings,
                "Ad cost per click": t.cpc,
                "Trend": s.label if s else "No data",
                "Keyword difficulty": t.keyword_difficulty,
                "Peak month": s.peak_month.strftime("%b %Y") if s and s.peak_month else None,
                "Low month": s.low_month.strftime("%b %Y") if s and s.low_month else None,
                "Seasonality (peak/low)": s.seasonality_ratio if s else None,
                "Latest vs 12-mo avg %": s.latest_vs_avg_pct if s else None,
                "Last 3 vs first 3 mo %": s.change_pct if s else None,
                "YoY %": s.yoy_pct if s else None,
                "Competing listings (summary)": t.competing_listings_alt,
                "Price low": t.price_low,
                "Price median": t.price_median,
                "Price high": t.price_high,
                "Top search country": (
                    f"{t.search_by_country[0].country} ({t.search_by_country[0].pct:.0f}%)"
                    if t.search_by_country and t.search_by_country[0].pct is not None
                    else None
                ),
                "Data updated": t.updated,
                "Source": t.source_url,
                "Related keywords": ", ".join(t.related_keywords[:15]),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=TREND_TEMPLATE_COLUMNS)
    return df.sort_values("Typical monthly searches", ascending=False, na_position="last")


def monthly_frame(monthly: pd.DataFrame) -> pd.DataFrame:
    """Long (keyword, month, searches) -> wide: one row per keyword, one column per month."""
    if monthly.empty:
        return monthly
    wide = monthly.pivot_table(index="keyword", columns="month", values="searches", aggfunc="last")
    wide.columns = [pd.Timestamp(c).strftime("%Y-%m") for c in wide.columns]
    return wide.reset_index()


def price_band_frame(trends: list[KeywordTrend]) -> pd.DataFrame:
    return pd.DataFrame([{"keyword": t.keyword, **t.price_bands} for t in trends])


def country_frame(trends: list[KeywordTrend], kind: str) -> pd.DataFrame:
    rows = []
    for t in trends:
        shares = t.search_by_country if kind == "search" else t.competition_by_country
        rows += [
            {"keyword": t.keyword, "country": c.country, "value": c.value, "pct": c.pct}
            for c in shares
        ]
    return pd.DataFrame(rows)


def snapshot_frame(snapshots: list[MarketSnapshot]) -> pd.DataFrame:
    rows = []
    for s in snapshots:
        d = s.model_dump(exclude={"price_bands"})
        d.update({f"band {k} %": v for k, v in s.price_bands.items()})
        rows.append(d)
    return pd.DataFrame(rows)


def workbook_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if df is None or df.empty:
                continue
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            ws.freeze_panes = "B2"
            for i, col in enumerate(df.columns, start=1):
                width = 50 if col in ("Source", "Related keywords") else max(10, len(str(col)) + 2)
                ws.column_dimensions[get_column_letter(i)].width = min(width, 50)
    return buf.getvalue()


def write_workbook(sheets: dict[str, pd.DataFrame], out_dir: Path, stem: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    path.write_bytes(workbook_bytes(sheets))
    return path
