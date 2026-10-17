"""Turn a keyword into ranked ListingRows by combining the browser scraper and the API.

Sources:
- "auto" (default): ranks come from the etsy.com search page (what shoppers see).
  With an API key, every other column comes from the API, so only the search page is
  loaded. Without a key, each listing page and shop page is loaded too.
- "browser": never call the API.
- "api": never open a browser; ranks follow the API's relevance order.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from typing import Literal

from .browser import BlockedError, EtsyBrowser
from .etsy_api import EtsyApi
from .listing_scraper import scrape_listing
from .models import ListingDetails, ListingRow, SearchHit, ShopStats
from .search_scraper import scrape_search
from .shop_scraper import scrape_shop

Source = Literal["auto", "browser", "api"]


def filter_label(exclude_digital: bool) -> str:
    return "default exclude digital" if exclude_digital else "default include digital"


def _first(*values):
    return next((v for v in values if v is not None), None)


def build_row(
    keyword: str,
    search_filter: str,
    hit: SearchHit,
    details: ListingDetails,
    shop: ShopStats,
    source: str,
) -> ListingRow:
    return ListingRow(
        target_keyword=keyword,
        search_filter=search_filter,
        rank=hit.rank,
        listing_link=hit.url,
        # The search card shows the shopper-facing price; listing/API data fills gaps.
        price_dollar=_first(hit.price, details.price),
        on_sales_price_dollar=hit.sale_price if hit.price is not None else details.sale_price,
        num_photos_video=details.num_photos_video,
        reviews=details.reviews,
        # Matches the research sheet: the stars on a search card are the shop's average.
        review_star=_first(hit.shop_rating, shop.shop_rating, details.review_star),
        is_best_seller=_first(hit.is_best_seller, details.is_best_seller),
        shop_name=_first(shop.shop_name, details.shop_name, hit.shop_name),
        shop_age_year=shop.shop_age_year,
        shop_total_sales=shop.shop_total_sales,
        shop_total_review=shop.shop_total_review,
        shop_total_product=shop.shop_total_product,
        is_ad=hit.is_ad,
        listing_id=hit.listing_id,
        title=hit.title,
        source=source,
    )


def run(
    keyword: str,
    top_n: int = 20,
    exclude_digital: bool = True,
    source: Source = "auto",
    api: EtsyApi | None = None,
    headless: bool | None = None,
    on_progress: Callable[[str], None] = print,
) -> list[ListingRow]:
    if source != "browser" and api is None:
        api = EtsyApi.from_env()
    if source == "api" and api is None:
        raise ValueError("source='api' needs ETSY_API_KEY (see .env.example)")
    if source == "browser":
        api = None

    label = filter_label(exclude_digital)
    use_browser = source != "api"
    browser_cm = (
        EtsyBrowser(headless=headless, on_status=on_progress) if use_browser else nullcontext()
    )

    with browser_cm as browser:
        on_progress(f"Searching Etsy for {keyword!r} (top {top_n})...")
        if use_browser:
            hits = scrape_search(browser, keyword, top_n, exclude_digital)
        else:
            hits = api.search_hits(keyword, top_n, exclude_digital)
        on_progress(f"Found {len(hits)} listings.")
        if not hits:
            return []

        details: dict[str, ListingDetails] = {}
        if api is not None:
            on_progress("Fetching listing details from the Etsy API...")
            details = api.listing_details([h.listing_id for h in hits])

        shop_cache: dict[str, ShopStats] = {}
        rows: list[ListingRow] = []
        for hit in hits:
            on_progress(f"[{hit.rank}/{len(hits)}] {hit.url}")
            d = details.get(hit.listing_id)
            row_source = "browser+api" if (use_browser and api) else ("api" if api else "browser")
            try:
                if d is None and use_browser:
                    d = scrape_listing(browser, hit.url)
                d = d or ListingDetails()

                shop_key = d.shop_id or hit.shop_id or d.shop_url
                if shop_key and shop_key not in shop_cache:
                    if api is not None and (d.shop_id or hit.shop_id):
                        shop_cache[shop_key] = api.shop_stats(d.shop_id or hit.shop_id)
                    elif use_browser and d.shop_url:
                        shop_cache[shop_key] = scrape_shop(browser, d.shop_url)
                shop = shop_cache.get(shop_key, ShopStats()) if shop_key else ShopStats()
            except BlockedError:
                raise
            except Exception as exc:  # keep going; one bad listing shouldn't sink the run
                on_progress(f"  warning: {type(exc).__name__}: {exc}")
                d, shop = d or ListingDetails(), ShopStats()
            rows.append(build_row(keyword, label, hit, d, shop, row_source))
    return rows
