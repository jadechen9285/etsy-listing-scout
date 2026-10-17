"""Read one etsy.com listing page: media count, item reviews, price, and shop link."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import selectors as S
from .models import ListingDetails
from .parsing import iter_json_ld, ld_type_is, parse_count, parse_price, parse_rating


def _product_ld(soup: BeautifulSoup) -> dict | None:
    scripts = [s.string or "" for s in soup.select("script[type='application/ld+json']")]
    for obj in iter_json_ld(scripts):
        if ld_type_is(obj, "Product"):
            return obj
    return None


def _ld_price(product: dict) -> float | None:
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return None
    return parse_price(str(offers.get("price") or offers.get("lowPrice") or ""))


def _select_first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    """Text of every node matching the first selector that matches anything."""
    for sel in selectors:
        nodes = soup.select(sel)
        if nodes:
            return " ".join(n.get_text(" ", strip=True) for n in nodes)
    return ""


def parse_listing_page(html: str) -> ListingDetails:
    soup = BeautifulSoup(html, "html.parser")
    product = _product_ld(soup) or {}
    page_text = soup.get_text(" ", strip=True)
    buy_box = _select_first_text(soup, S.BUY_BOX)

    # Prices: the buy box says "Price: $12.39  Original Price: $15.49" when on sale.
    price_text = _select_first_text(soup, S.LISTING_PRICE) or buy_box
    current = None
    if m := S.LISTING_PRICE_TEXT.search(price_text):
        current = parse_price(m.group(1))
    current = current or _ld_price(product)
    original = None
    if m := S.ORIGINAL_PRICE_TEXT.search(price_text):
        original = parse_price(m.group(1))
    if original and current and original > current:
        price, sale_price = original, current
    else:
        price, sale_price = current or original, None

    # Media: carousel thumbnails, else the JSON-LD image list; plus any video.
    photos = 0
    for sel in S.CAROUSEL_ITEM:
        photos = len(soup.select(sel))
        if photos:
            break
    if not photos:
        images = product.get("image")
        photos = len(images) if isinstance(images, list) else (1 if images else 0)
    has_video = any(soup.select_one(sel) is not None for sel in S.VIDEO)
    # A video usually also occupies a carousel slot; only add it when it was not counted.
    media = photos + (1 if has_video and not soup.select("li [data-carousel-video]") else 0)

    reviews = None
    for pattern in S.ITEM_REVIEWS_TEXT:
        if m := pattern.search(page_text):
            reviews = parse_count(m.group(1))
            break
    rating = product.get("aggregateRating") or {}
    if reviews is None and rating.get("reviewCount") is not None:
        reviews = parse_count(str(rating["reviewCount"]))

    shop_url = None
    for sel in S.SHOP_LINK:
        node = soup.select_one(sel)
        if node is not None and node.get("href"):
            shop_url = urljoin("https://www.etsy.com", node["href"].split("?")[0])
            break
    brand = product.get("brand")
    shop_name = brand.get("name") if isinstance(brand, dict) else (brand or None)
    if not shop_name and shop_url:
        shop_name = shop_url.rstrip("/").rsplit("/", 1)[-1]

    return ListingDetails(
        price=price,
        sale_price=sale_price,
        num_photos_video=media or None,
        reviews=reviews,
        review_star=parse_rating(str(rating.get("ratingValue") or "")),
        is_best_seller=bool(S.BESTSELLER_TEXT.search(buy_box)) if buy_box else None,
        shop_name=shop_name,
        shop_url=shop_url,
        is_digital=bool(S.DIGITAL_TEXT.search(buy_box or page_text[:20000])),
    )


def scrape_listing(browser, url: str) -> ListingDetails:
    return parse_listing_page(browser.get_html(url))
