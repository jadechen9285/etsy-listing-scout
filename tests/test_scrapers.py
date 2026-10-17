from pathlib import Path

from etsy_scout.browser import is_blocked
from etsy_scout.listing_scraper import parse_listing_page
from etsy_scout.search_scraper import parse_search_page, search_url
from etsy_scout.shop_scraper import parse_shop_page

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_search_page_cards_in_order_and_deduplicated():
    cards = parse_search_page(read("search_sample.html"))
    assert [c["listing_id"] for c in cards] == ["4460064203", "4396370373"]

    first, second = cards
    assert first["url"] == "https://www.etsy.com/listing/4460064203/adhd-brain-dump-notepad"
    assert first["price"] == 15.49 and first["sale_price"] == 12.39
    assert first["is_best_seller"] is True and first["is_ad"] is False
    assert first["shop_rating"] == 4.9 and first["shop_id"] == "111"

    assert second["price"] == 32.94 and second["sale_price"] is None
    assert second["is_ad"] is True and second["is_best_seller"] is False


def test_search_url_filters_physical():
    assert "is_physical=true" in search_url("adhd notebook")
    assert "is_physical" not in search_url("adhd notebook", exclude_digital=False)
    assert "q=adhd+notebook" in search_url("adhd notebook", page=2)


def test_listing_page():
    d = parse_listing_page(read("listing_sample.html"))
    assert d.price == 15.49 and d.sale_price == 12.39
    assert d.num_photos_video == 9  # 8 carousel slots + 1 video
    assert d.reviews == 1  # "Item reviews (1)" wins over JSON-LD
    assert d.review_star == 5.0
    assert d.is_best_seller is True
    assert d.shop_name == "FocusPaperCo"
    assert d.shop_url == "https://www.etsy.com/shop/FocusPaperCo"


def test_shop_page():
    s = parse_shop_page(read("shop_sample.html"))
    assert s.shop_name == "FocusPaperCo"
    assert s.shop_total_sales == 1529
    assert s.shop_total_review == 207
    assert s.shop_total_product == 123
    assert s.shop_rating == 4.9
    assert s.shop_age_year is not None and s.shop_age_year > 6


def test_block_detection():
    blocked = '<html><script src="https://ct.captcha-delivery.com/c.js"></script></html>'
    assert is_blocked(blocked)
    assert not is_blocked(read("search_sample.html"))
