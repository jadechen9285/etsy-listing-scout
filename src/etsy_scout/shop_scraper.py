"""Read shop-level stats from an etsy.com shop page (fallback when no API key is set)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from . import selectors as S
from .models import ShopStats
from .parsing import parse_count, parse_rating, years_since_year


def parse_shop_page(html: str) -> ShopStats:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    sales = parse_count(m.group(1)) if (m := S.SHOP_SALES_TEXT.search(text)) else None

    age = None
    if m := S.SHOP_SINCE_TEXT.search(text):
        age = years_since_year(m.group(1))
    elif m := S.SHOP_YEARS_TEXT.search(text):
        age = float(m.group(1))

    items = None
    for pattern in S.SHOP_ITEMS_TEXT:
        if m := pattern.search(text):
            items = parse_count(m.group(1))
            break

    reviews = None
    for pattern in S.SHOP_REVIEWS_TEXT:
        if m := pattern.search(text):
            reviews = parse_count(m.group(1))
            break

    rating = parse_rating(m.group(1)) if (m := S.SHOP_RATING_TEXT.search(text)) else None

    h1 = soup.select_one("h1")
    return ShopStats(
        shop_name=h1.get_text(strip=True) if h1 else None,
        shop_age_year=age,
        shop_total_sales=sales,
        shop_total_review=reviews,
        shop_total_product=items,
        shop_rating=rating,
    )


def scrape_shop(browser, shop_url: str) -> ShopStats:
    return parse_shop_page(browser.get_html(shop_url))
