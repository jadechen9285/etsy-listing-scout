"""Read the ranked listing cards from an etsy.com search results page."""

from __future__ import annotations

from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from . import selectors as S
from .models import SearchHit
from .parsing import canonical_listing_url, listing_id_from_url, parse_price, parse_rating

PAGE_SIZE_HINT = 48  # Etsy shows ~48 cards per page; used only to bound pagination


def search_url(keyword: str, page: int = 1, exclude_digital: bool = True) -> str:
    params = {"q": keyword, "order": "most_relevant", "ref": "pagination", "page": page}
    if exclude_digital:
        params["is_physical"] = "true"
    return "https://www.etsy.com/search?" + urlencode(params)


def _first(node: Tag, selectors: list[str]) -> Tag | None:
    for sel in selectors:
        found = node.select_one(sel)
        if found is not None:
            return found
    return None


def _text(node: Tag | None) -> str:
    return node.get_text(" ", strip=True) if node is not None else ""


def _card_rating(card: Tag) -> float | None:
    node = card.select_one("input[name='rating']") or card.select_one("[aria-label*='star' i]")
    if node is None:
        return None
    return parse_rating(node.get("value") or node.get("aria-label") or "")


def _parse_card(card: Tag) -> dict | None:
    link = _first(card, S.CARD_LINK)
    href = link.get("href") if link else None
    listing_id = card.get("data-listing-id") or (listing_id_from_url(href) if href else None)
    if not listing_id or not href:
        return None
    text = card.get_text(" ", strip=True)

    title_node = _first(card, S.CARD_TITLE)
    title = (title_node.get("title") if title_node else None) or _text(title_node) or None
    if not title and link is not None:
        title = link.get("title") or None

    current = parse_price(_text(_first(card, S.CARD_CURRENT_PRICE)))
    original = parse_price(_text(_first(card, S.CARD_ORIGINAL_PRICE)))
    if m := S.ORIGINAL_PRICE_TEXT.search(text):
        original = parse_price(m.group(1))
    if m := S.SALE_PRICE_TEXT.search(text):
        current = parse_price(m.group(1))

    if original and current and original > current:
        price, sale_price = original, current
    else:
        price, sale_price = current or original, None

    is_ad = bool(S.AD_TEXT.search(text)) or any(h in href for h in S.AD_URL_HINTS)
    shop_node = _first(card, S.CARD_SHOP_NAME)
    shop_name = (shop_node.get("data-shop-name") if shop_node else None) or _text(shop_node) or None

    return {
        "listing_id": str(listing_id),
        "url": canonical_listing_url(href),
        "title": title,
        "is_ad": is_ad,
        "price": price,
        "sale_price": sale_price,
        "is_best_seller": bool(S.BESTSELLER_TEXT.search(text)),
        "shop_name": shop_name,
        "shop_id": card.get("data-shop-id"),
        "shop_rating": _card_rating(card),
    }


def parse_search_page(html: str) -> list[dict]:
    """Cards in display order, de-duplicated, from the main results grid."""
    soup = BeautifulSoup(html, "html.parser")
    container = None
    for sel in S.SEARCH_RESULTS_CONTAINER:
        container = soup.select_one(sel)
        if container is not None and container.select_one(S.SEARCH_CARD):
            break
    container = container or soup

    seen: set[str] = set()
    cards: list[dict] = []
    for node in container.select(S.SEARCH_CARD):
        # Skip inner elements that repeat the id of their parent card.
        parent = node.find_parent(attrs={"data-listing-id": True})
        if parent is not None and parent.get("data-listing-id") == node.get("data-listing-id"):
            continue
        card = _parse_card(node)
        if card and card["listing_id"] not in seen:
            seen.add(card["listing_id"])
            cards.append(card)
    return cards


def scrape_search(
    browser, keyword: str, top_n: int, exclude_digital: bool = True
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    seen: set[str] = set()
    max_pages = max(1, -(-top_n // PAGE_SIZE_HINT) + 2)
    for page in range(1, max_pages + 1):
        cards = parse_search_page(browser.get_html(search_url(keyword, page, exclude_digital)))
        new = [c for c in cards if c["listing_id"] not in seen]
        if not new:
            break
        for c in new:
            seen.add(c["listing_id"])
            hits.append(SearchHit(rank=len(hits) + 1, rank_method="website", **c))
            if len(hits) >= top_n:
                return hits
    return hits
