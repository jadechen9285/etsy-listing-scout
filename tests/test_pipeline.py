import httpx
import pandas as pd

from etsy_scout.etsy_api import EtsyApi
from etsy_scout.export import COLUMNS, excel_bytes, to_dataframe
from etsy_scout.models import TEMPLATE_COLUMNS
from etsy_scout.pipeline import run

SHOP_CREATED = 1_600_000_000  # 2020-09-13


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
        ids = request.url.params["listing_ids"].split(",")
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "listing_id": int(i),
                        "shop_id": 9,
                        "price": {"amount": 1549, "divisor": 100},
                        "listing_type": "physical",
                        "images": [{}, {}, {}],
                        "videos": [{}],
                        "shop": {"shop_name": "FocusPaperCo"},
                    }
                    for i in ids
                ]
            },
        )
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
    return EtsyApi("key", "secret", client=client, min_interval=0)


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


def test_export_matches_template_columns():
    rows = run("adhd notebook", top_n=2, source="api", api=make_api(), on_progress=lambda _: None)
    df = to_dataframe(rows)
    assert list(df.columns[: len(TEMPLATE_COLUMNS)]) == TEMPLATE_COLUMNS
    assert list(df.columns) == COLUMNS
    assert set(df["is_ad"]) == {"F"}
    back = pd.read_excel(__import__("io").BytesIO(excel_bytes(df)), sheet_name="competitor_listing")
    assert len(back) == 2 and back.loc[0, "listing_link"] == "https://www.etsy.com/listing/1/a"
