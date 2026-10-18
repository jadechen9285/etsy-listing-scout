import httpx
import pandas as pd

from etsy_scout.etsy_api import EtsyApi
from etsy_scout.export import COLUMNS, excel_bytes, to_dataframe
from etsy_scout.fx import FxRates
from etsy_scout.models import TEMPLATE_COLUMNS
from etsy_scout.pipeline import run

SHOP_CREATED = 1_600_000_000  # 2020-09-13


def usd(amount: int, currency: str = "USD") -> dict:
    return {"amount": amount, "divisor": 100, "currency_code": currency}


# Listing 1: USD, not on sale. Listing 3: a GBP seller with a 25% sale and free shipping.
BATCH = {
    "1": {
        "listing_id": 1,
        "shop_id": 9,
        "price": usd(1549),
        "listing_type": "physical",
        "images": [{}, {}, {}],
        "videos": [{}],
        "shop": {"shop_name": "FocusPaperCo"},
        "views": 1200,
        "num_favorers": 85,
        "tags": ["adhd planner", "focus journal"],
        "materials": ["paper", "cardstock"],
        "buyer_price": {
            "original_price": usd(1549),
            "has_discount": False,
            "discounted_price": None,
            "discount_percentage": None,
            "shipping_cost": usd(599),
            "is_free_shipping": False,
        },
    },
    "3": {
        "listing_id": 3,
        "shop_id": 9,
        "price": usd(1600, "GBP"),
        "listing_type": "physical",
        "images": [{}],
        "shop": {"shop_name": "FocusPaperCo"},
        "views": 40,
        "num_favorers": 3,
        "tags": [],
        "materials": [],
        "buyer_price": {
            "original_price": usd(1600, "GBP"),
            "has_discount": True,
            "discounted_price": usd(1200, "GBP"),
            "discount_percentage": 25,
            "shipping_cost": None,
            "is_free_shipping": True,
        },
    },
}


def fx_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"base": "USD", "date": "2026-10-16", "rates": {"GBP": 0.8}})


def handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["x-api-key"] == "key:secret"
    path = request.url.path
    if path.endswith("/listings/active"):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "listing_id": 1,
                        "url": "https://www.etsy.com/listing/1/a?ref=x",
                        "title": "A",
                        "price": {"amount": 1549, "divisor": 100},
                        "shop_id": 9,
                        "listing_type": "physical",
                    },
                    {
                        "listing_id": 2,
                        "url": "https://www.etsy.com/listing/2/b",
                        "title": "B",
                        "price": {"amount": 500, "divisor": 100},
                        "shop_id": 9,
                        "listing_type": "download",
                    },
                    {
                        "listing_id": 3,
                        "url": "https://www.etsy.com/listing/3/c",
                        "title": "C",
                        "price": {"amount": 2000, "divisor": 100},
                        "shop_id": 9,
                        "listing_type": "physical",
                    },
                ]
            },
        )
    if path.endswith("/listings/batch"):
        assert "BuyerPrice" in request.url.params["includes"]
        assert request.url.params["buyer_country"] == "US"
        ids = request.url.params["listing_ids"].split(",")
        return httpx.Response(200, json={"results": [BATCH[i] for i in ids]})
    if "/reviews" in path:
        return httpx.Response(200, json={"count": 2, "results": [{"rating": 5}, {"rating": 4}]})
    if path.endswith("/shops/9"):
        return httpx.Response(
            200,
            json={
                "shop_name": "FocusPaperCo",
                "create_date": SHOP_CREATED,
                "transaction_sold_count": 1529,
                "review_count": 207,
                "review_average": 4.86,
                "listing_active_count": 123,
            },
        )
    return httpx.Response(404)


def make_api() -> EtsyApi:
    client = httpx.Client(
        base_url="https://openapi.etsy.com/v3/application", transport=httpx.MockTransport(handler)
    )
    fx = FxRates(client=httpx.Client(transport=httpx.MockTransport(fx_handler)))
    return EtsyApi("key", "secret", client=client, min_interval=0, fx=fx)


def test_api_only_run_skips_digital_and_fills_columns():
    rows = run("adhd notebook", top_n=2, source="api", api=make_api(), on_progress=lambda _: None)
    assert [r.listing_id for r in rows] == ["1", "3"]
    assert [r.rank for r in rows] == [1, 2]
    r = rows[0]
    assert r.listing_link == "https://www.etsy.com/listing/1/a"
    assert r.price_dollar == 15.49
    assert r.num_photos_video == 4
    assert r.reviews == 2
    assert r.review_star == 4.9  # shop average, as on the search card
    assert r.shop_name == "FocusPaperCo"
    assert r.shop_total_sales == 1529 and r.shop_total_review == 207
    assert r.shop_total_product == 123
    assert r.shop_age_year and r.shop_age_year > 6
    assert r.search_filter == "default exclude digital"
    assert r.on_sales_price_dollar is None
    assert (r.price_original, r.price_currency) == (15.49, "USD")
    assert r.shipping_cost_usd == 5.99 and r.free_shipping is False
    assert (r.views, r.num_favorers) == (1200, 85)
    assert r.tags == ["adhd planner", "focus journal"]
    assert r.materials == ["paper", "cardstock"]


def test_non_usd_prices_are_converted_and_sales_detected():
    rows = run("adhd notebook", top_n=2, source="api", api=make_api(), on_progress=lambda _: None)
    gbp = rows[1]
    assert (gbp.price_original, gbp.price_currency) == (16.0, "GBP")
    assert gbp.price_dollar == 20.0  # 16 GBP / 0.8
    assert gbp.on_sales_price_dollar == 15.0  # 12 GBP sale price
    assert gbp.discount_pct == 25
    assert gbp.free_shipping is True and gbp.shipping_cost_usd is None


def test_export_matches_template_columns():
    rows = run("adhd notebook", top_n=2, source="api", api=make_api(), on_progress=lambda _: None)
    df = to_dataframe(rows)
    assert list(df.columns[: len(TEMPLATE_COLUMNS)]) == TEMPLATE_COLUMNS
    assert list(df.columns) == COLUMNS
    assert set(df["is_ad"]) == {"F"}
    assert df.loc[0, "tags"] == "adhd planner, focus journal"
    assert df.loc[0, "materials"] == "paper, cardstock"
    assert list(df["free_shipping"]) == ["F", "T"]
    back = pd.read_excel(__import__("io").BytesIO(excel_bytes(df)), sheet_name="competitor_listing")
    assert len(back) == 2 and back.loc[0, "listing_link"] == "https://www.etsy.com/listing/1/a"


def test_default_source_requires_api_key(monkeypatch):
    import pytest

    monkeypatch.delenv("ETSY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ETSY_API_KEY"):
        run("adhd notebook", on_progress=lambda _: None)


def test_rejected_key_gives_actionable_error():
    import pytest

    from etsy_scout.etsy_api import EtsyApiError

    client = httpx.Client(
        base_url="https://openapi.etsy.com/v3/application",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(403, json={"error": "API key not found or not active"})
        ),
    )
    api = EtsyApi("key", "secret", client=client, min_interval=0)
    with pytest.raises(EtsyApiError, match="developers/your-apps"):
        run("adhd notebook", source="api", api=api, on_progress=lambda _: None)
