from datetime import UTC, datetime

import pytest

from etsy_scout.parsing import (
    canonical_listing_url,
    listing_id_from_url,
    parse_count,
    parse_price,
    parse_rating,
    years_since,
    years_since_year,
)

NOW = datetime(2026, 10, 17, tzinfo=UTC)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,234 sales", 1234),
        ("(10.8k)", 10800),
        ("2.1M", 2100000),
        ("207", 207),
        ("", None),
        (None, None),
        ("no digits", None),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


def test_parse_price_and_rating():
    assert parse_price("USD 1,015.00+") == 1015.0
    assert parse_price("$15.49") == 15.49
    assert parse_rating("4.9 out of 5 stars") == 4.9
    assert parse_rating("12") is None


def test_years_since():
    assert years_since(datetime(2020, 10, 17, tzinfo=UTC), NOW) == 6.0
    assert years_since(int(datetime(2025, 10, 17, tzinfo=UTC).timestamp()), NOW) == 1.0
    assert years_since_year("On Etsy since 2019", NOW) == 7.3


def test_listing_urls():
    url = (
        "https://www.etsy.com/listing/4460064203/adhd-brain-dump-notepad-a5-daily-to-do"
        "?ls=s&ga_order=most_relevant&ref=sr_gallery-1-1"
    )
    assert listing_id_from_url(url) == "4460064203"
    assert canonical_listing_url(url) == (
        "https://www.etsy.com/listing/4460064203/adhd-brain-dump-notepad-a5-daily-to-do"
    )
    assert canonical_listing_url("/listing/123") == "https://www.etsy.com/listing/123"
