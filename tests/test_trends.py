from datetime import date
from pathlib import Path

import httpx
import pandas as pd
import pytest

from etsy_scout.etsy_api import EtsyApi
from etsy_scout.fx import FxRates
from etsy_scout.trends import history
from etsy_scout.trends.analysis import price_stats, summarize_trend
from etsy_scout.trends.cli import rankhero_url
from etsy_scout.trends.export import trend_summary_frame, workbook_bytes
from etsy_scout.trends.market_snapshot import take_snapshot
from etsy_scout.trends.models import TREND_TEMPLATE_COLUMNS, MonthlySearches
from etsy_scout.trends.rankhero_import import (
    NotARankHeroPage,
    import_rankhero_files,
    parse_rankhero_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


def series(values, start_year=2024, start_month=9):
    out = []
    y, m = start_year, start_month
    for v in values:
        out.append(MonthlySearches(month=date(y, m, 1), searches=v))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_parse_rankhero_page():
    t = parse_rankhero_page((FIXTURES / "rankhero_sample.html").read_text())
    assert t.keyword == "focus journal"
    assert t.source_url == "https://www.rankhero.com/keywords/focus-journal"
    assert t.updated == date(2026, 8, 6)
    assert t.monthly_searches == 2400
    assert t.competing_listings == 10250
    assert t.competing_listings_alt == 9100
    assert t.cpc == 1.15
    assert t.keyword_difficulty == 38
    assert (t.price_low, t.price_median, t.price_high) == (2.5, 14.2, 60.0)
    assert t.price_sample_size == 50
    assert t.price_bands == {"Under $10": 30, "$10 - $25": 55, "$25 - $50": 12, "$50 - $100": 3}
    assert [(c.country, c.value, c.pct) for c in t.search_by_country] == [
        ("USA", 1500, 62.0),
        ("UK", 400, 17.0),
    ]
    assert t.competition_by_country[0].value == 8000
    assert len(t.monthly) == 12 and t.monthly[0].month == date(2025, 9, 1)
    assert t.related_keywords == ["focus planner", "deep work journal"]
    assert t.summary.label == "Rising +38%"


def test_non_rankhero_page_is_skipped(tmp_path):
    with pytest.raises(NotARankHeroPage):
        parse_rankhero_page("<html><body><h1>hello</h1></body></html>")
    (tmp_path / "other.html").write_text("<html><body>nothing</body></html>")
    (tmp_path / "rh.html").write_text((FIXTURES / "rankhero_sample.html").read_text())
    trends, warnings = import_rankhero_files([tmp_path])
    assert [t.keyword for t in trends] == ["focus journal"]
    assert len(warnings) == 1 and "other.html" in warnings[0]


@pytest.mark.parametrize(
    ("values", "label"),
    [
        ([100] * 12, "Stable (+0%)"),
        ([100] * 6 + [150] * 6, "Rising +50%"),
        ([150] * 6 + [100] * 6, "Falling -33%"),
        (
            [100, 100, 150, 250, 250, 100, 100, 100, 90, 90, 90, 100],
            "Seasonal: peak Dec, low May (2.8x)",
        ),
    ],
)
def test_trend_labels(values, label):
    assert summarize_trend(series(values)).label == label


def test_yoy_label_with_two_years_of_history():
    s = summarize_trend(series([100] * 12 + [130] * 12))
    assert s.yoy_pct == 30.0
    assert s.label == "Rising +30% YoY"


def test_price_stats_bands():
    stats = price_stats([5, 8, 12, 20, 30, 120])
    assert stats["price_min"] == 5 and stats["price_max"] == 120
    assert stats["price_median"] == 16.0
    assert stats["price_bands"]["Under $10"] == pytest.approx(33.3)
    assert stats["price_bands"]["$100+"] == pytest.approx(16.7)


def test_market_snapshot_from_api():
    def handler(request):
        offset = int(request.url.params["offset"])
        results = (
            [
                {
                    "listing_id": i,
                    "price": {
                        "amount": 1000 + i * 100,
                        "divisor": 100,
                        "currency_code": "GBP" if i == 2 else "USD",
                    },
                    "listing_type": "download" if i == 0 else "physical",
                    "num_favorers": 10,
                }
                for i in range(offset, offset + 3)
            ]
            if offset == 0
            else []
        )
        return httpx.Response(200, json={"count": 9876, "results": results})

    client = httpx.Client(base_url="https://x", transport=httpx.MockTransport(handler))
    fx = FxRates(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"rates": {"GBP": 0.5}})
            )
        )
    )
    snap = take_snapshot(EtsyApi("k", client=client, min_interval=0, fx=fx), "focus journal")
    assert snap.competing_listings == 9876
    assert snap.sample_size == 2  # the digital listing is excluded
    assert (snap.price_min, snap.price_max) == (11.0, 24.0)  # 12 GBP -> 24 USD
    assert snap.avg_favorites == 10


def test_history_upsert_and_monthly_merge(tmp_path):
    t = parse_rankhero_page((FIXTURES / "rankhero_sample.html").read_text())
    history.append_history([history.trend_record(t)], tmp_path)
    history.append_history([history.trend_record(t)], tmp_path)  # same day: no duplicate
    assert len(history.load_history(tmp_path)) == 1

    history.merge_monthly([t], tmp_path)
    older = t.model_copy(deep=True)
    for m in older.monthly:
        m.month = m.month.replace(year=m.month.year - 1)
    history.merge_monthly([older], tmp_path)
    full = history.monthly_series("Focus Journal", tmp_path)
    assert len(full) == 24
    assert summarize_trend(full).yoy_pct == 0.0


def test_summary_frame_starts_with_template_columns():
    t = parse_rankhero_page((FIXTURES / "rankhero_sample.html").read_text())
    df = trend_summary_frame([t])
    assert list(df.columns[: len(TREND_TEMPLATE_COLUMNS)]) == TREND_TEMPLATE_COLUMNS
    back = pd.read_excel(__import__("io").BytesIO(workbook_bytes({"s": df})), sheet_name="s")
    assert back.loc[0, "Keyword"] == "focus journal"


def test_rankhero_url():
    assert (
        rankhero_url("ADHD  Daily Planner")
        == "https://www.rankhero.com/keywords/adhd-daily-planner"
    )
