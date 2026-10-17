"""Turn raw series and prices into the summary numbers the research sheet uses."""

from __future__ import annotations

import statistics

from .models import MonthlySearches, TrendSummary

PRICE_BANDS = [
    ("Under $10", 0, 10),
    ("$10 - $25", 10, 25),
    ("$25 - $50", 25, 50),
    ("$50 - $100", 50, 100),
    ("$100+", 100, float("inf")),
]
RISING, FALLING = 15.0, -15.0  # % change thresholds for the trend label
SEASONAL_RATIO = 1.8  # peak month at least 1.8x the low month


def summarize_trend(series: list[MonthlySearches]) -> TrendSummary | None:
    """Label a monthly series: direction (last 3 vs first 3 months) and seasonality."""
    if not series:
        return None
    values = [m.searches for m in series]
    if max(values) == 0:
        return TrendSummary(label="No search volume")

    change = None
    if len(series) >= 6:
        first = statistics.fmean(values[:3])
        last = statistics.fmean(values[-3:])
        change = round((last - first) / first * 100, 1) if first else None

    recent = series[-12:]  # season is judged on the latest year only
    peak = max(recent, key=lambda m: m.searches)
    low = min(recent, key=lambda m: m.searches)
    ratio = round(peak.searches / low.searches, 2) if low.searches else None

    avg = statistics.fmean(values[-12:])
    latest_vs_avg = round((values[-1] - avg) / avg * 100, 1) if avg else None

    yoy = None
    if len(series) >= 24:
        # Enough history for a real year-over-year comparison: last 12 vs prior 12 months.
        prior = sum(values[-24:-12])
        yoy = round((sum(values[-12:]) - prior) / prior * 100, 1) if prior else None

    seasonal = ratio is None or ratio >= SEASONAL_RATIO
    season = f"peak {peak.month:%b}, low {low.month:%b}" + (f" ({ratio:.1f}x)" if ratio else "")
    if yoy is not None:
        if yoy >= RISING:
            label = f"Rising {yoy:+.0f}% YoY"
        elif yoy <= FALLING:
            label = f"Falling {yoy:+.0f}% YoY"
        else:
            label = f"Flat YoY ({yoy:+.0f}%)"
        if seasonal:
            label += f", seasonal: {season}"
    # 12 months cannot separate seasonality from growth, so a seasonal keyword is labelled
    # by its season rather than by a "rising/falling" that may only be the off-season.
    elif seasonal:
        label = f"Seasonal: {season}"
    elif change is None:
        label = "Not enough data"
    elif change >= RISING:
        label = f"Rising {change:+.0f}%"
    elif change <= FALLING:
        label = f"Falling {change:+.0f}%"
    else:
        label = f"Stable ({change:+.0f}%)"

    return TrendSummary(
        label=label,
        change_pct=change,
        peak_month=peak.month,
        low_month=low.month,
        seasonality_ratio=ratio,
        latest_vs_avg_pct=latest_vs_avg,
        yoy_pct=yoy,
    )


def price_stats(prices: list[float]) -> dict:
    """min / quartiles / max and the share of prices in each RankHero-style band."""
    prices = sorted(p for p in prices if p is not None)
    if not prices:
        return {}
    q = statistics.quantiles(prices, n=4) if len(prices) >= 2 else [prices[0]] * 3
    bands = {
        name: round(sum(lo <= p < hi for p in prices) / len(prices) * 100, 1)
        for name, lo, hi in PRICE_BANDS
    }
    return {
        "price_min": prices[0],
        "price_p25": round(q[0], 2),
        "price_median": round(statistics.median(prices), 2),
        "price_p75": round(q[2], 2),
        "price_max": prices[-1],
        "price_bands": bands,
    }
