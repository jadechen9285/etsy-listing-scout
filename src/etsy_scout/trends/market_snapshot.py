"""Measure a keyword's Etsy market directly from the Open API (fully automatic)."""

from __future__ import annotations

import statistics
from datetime import date

from ..etsy_api import EtsyApi
from .analysis import price_stats
from .models import MarketSnapshot


def take_snapshot(
    api: EtsyApi, keyword: str, sample_size: int = 100, exclude_digital: bool = True
) -> MarketSnapshot:
    """Competing-listing count plus price stats of the top `sample_size` relevant listings.

    `competing_listings` is Etsy's total match count for the keyword, which covers all
    listing types; the digital filter only applies to the price sample. Prices are
    regular (not sale) prices converted to USD.
    """
    total = None
    items: list[dict] = []
    offset = 0
    while len(items) < sample_size and offset < 1000:
        page = api.search_page(keyword, limit=100, offset=offset)
        total = page.get("count", total)
        results = page.get("results", [])
        if not results:
            break
        offset += len(results)
        for item in results:
            if exclude_digital and item.get("listing_type") == "download":
                continue
            items.append(item)
    items = items[:sample_size]

    # Etsy prices are in each seller's currency; compare them in USD.
    prices = [p for i in items if (p := api.fx.money_to_usd(i.get("price"))) is not None]
    favorites = [i["num_favorers"] for i in items if i.get("num_favorers") is not None]
    return MarketSnapshot(
        snapshot_date=date.today(),
        keyword=keyword,
        exclude_digital=exclude_digital,
        competing_listings=total,
        sample_size=len(items),
        avg_favorites=round(statistics.fmean(favorites), 1) if favorites else None,
        **price_stats(prices),
    )
