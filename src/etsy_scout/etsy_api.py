"""Minimal client for the public parts of the Etsy Open API v3.

Only API-key endpoints are used (no OAuth): keyword search, listing batch,
listing reviews, and shop info. See https://developers.etsy.com/documentation/
"""

from __future__ import annotations

import os
import time

import httpx

from .models import ListingDetails, SearchHit, ShopStats
from .parsing import canonical_listing_url, years_since

BASE_URL = "https://openapi.etsy.com/v3/application"


class EtsyApiError(RuntimeError):
    pass


def _money(price: dict | None) -> float | None:
    if not price or price.get("divisor") in (None, 0):
        return None
    return round(price["amount"] / price["divisor"], 2)


class EtsyApi:
    def __init__(
        self,
        api_key: str,
        shared_secret: str | None = None,
        client: httpx.Client | None = None,
        min_interval: float = 0.25,
    ):
        # Etsy expects "keystring:shared_secret" in x-api-key; older apps take the keystring.
        key = f"{api_key}:{shared_secret}" if shared_secret else api_key
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=30)
        self._headers = {"x-api-key": key}
        self._min_interval = min_interval
        self._last_call = 0.0

    @classmethod
    def from_env(cls) -> EtsyApi | None:
        key = os.getenv("ETSY_API_KEY")
        if not key:
            return None
        return cls(key, os.getenv("ETSY_SHARED_SECRET") or None)

    def _get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(4):
            wait = self._min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            resp = self._client.get(path, params=params, headers=self._headers)
            if resp.status_code == 429:
                time.sleep(2**attempt)
                continue
            if resp.status_code in (401, 403):
                raise EtsyApiError(
                    f"Etsy rejected the API key ({resp.status_code}: {resp.text[:200].strip()}). "
                    "Check that your app is approved/active at "
                    "https://www.etsy.com/developers/your-apps and that ETSY_API_KEY is the "
                    "Keystring and ETSY_SHARED_SECRET the Shared secret."
                )
            if resp.status_code >= 400:
                raise EtsyApiError(f"GET {path} -> {resp.status_code}: {resp.text[:300]}")
            return resp.json()
        raise EtsyApiError(f"GET {path} rate-limited after retries")

    # --- endpoints -----------------------------------------------------------

    def search(self, keyword: str, limit: int = 100, offset: int = 0) -> list[dict]:
        data = self._get(
            "/listings/active",
            {
                "keywords": keyword,
                "limit": limit,
                "offset": offset,
                "sort_on": "score",
                "sort_order": "desc",
            },
        )
        return data.get("results", [])

    def listings_batch(self, listing_ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for i in range(0, len(listing_ids), 100):
            chunk = listing_ids[i : i + 100]
            data = self._get(
                "/listings/batch",
                {"listing_ids": ",".join(chunk), "includes": "Images,Videos,Shop"},
            )
            for item in data.get("results", []):
                out[str(item["listing_id"])] = item
        return out

    def listing_review_stats(self, listing_id: str) -> tuple[int | None, float | None]:
        """(review count, average rating) for one listing."""
        data = self._get(f"/listings/{listing_id}/reviews", {"limit": 100})
        count = data.get("count")
        ratings = [r["rating"] for r in data.get("results", []) if r.get("rating") is not None]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else None
        return count, avg

    def shop(self, shop_id: str) -> dict:
        return self._get(f"/shops/{shop_id}")

    # --- conversions to our models -------------------------------------------

    def search_hits(self, keyword: str, top_n: int, exclude_digital: bool) -> list[SearchHit]:
        """Top N results in the API's relevance order (which may differ from etsy.com)."""
        hits: list[SearchHit] = []
        offset = 0
        while len(hits) < top_n and offset < 1000:
            page = self.search(keyword, limit=100, offset=offset)
            if not page:
                break
            offset += len(page)
            for item in page:
                if exclude_digital and item.get("listing_type") == "download":
                    continue
                hits.append(
                    SearchHit(
                        rank=len(hits) + 1,
                        listing_id=str(item["listing_id"]),
                        url=canonical_listing_url(item.get("url", "")),
                        title=item.get("title"),
                        price=_money(item.get("price")),
                        shop_id=str(item["shop_id"]) if item.get("shop_id") else None,
                    )
                )
                if len(hits) >= top_n:
                    break
        return hits

    def listing_details(self, listing_ids: list[str]) -> dict[str, ListingDetails]:
        raw = self.listings_batch(listing_ids)
        out: dict[str, ListingDetails] = {}
        for lid, item in raw.items():
            shop = item.get("shop") or {}
            media = len(item.get("images") or []) + len(item.get("videos") or [])
            reviews, stars = self.listing_review_stats(lid)
            out[lid] = ListingDetails(
                price=_money(item.get("price")),
                num_photos_video=media or None,
                reviews=reviews,
                review_star=stars,
                shop_id=str(item["shop_id"]) if item.get("shop_id") else None,
                shop_name=shop.get("shop_name"),
                is_digital=item.get("listing_type") == "download",
            )
        return out

    def shop_stats(self, shop_id: str) -> ShopStats:
        s = self.shop(shop_id)
        return ShopStats(
            shop_name=s.get("shop_name"),
            shop_age_year=years_since(s.get("create_date") or s.get("created_timestamp")),
            shop_total_sales=s.get("transaction_sold_count"),
            shop_total_review=s.get("review_count"),
            shop_total_product=s.get("listing_active_count"),
            shop_rating=round(s["review_average"], 1) if s.get("review_average") else None,
        )
