"""Minimal client for the public parts of the Etsy Open API v3.

Only API-key endpoints are used (no OAuth): keyword search, listing batch,
listing reviews, and shop info. See https://developers.etsy.com/documentation/
"""

from __future__ import annotations

import os
import time

import httpx

from .fx import FxRates, money
from .models import ListingDetails, SearchHit, ShopStats
from .parsing import canonical_listing_url, years_since
from .ranking import expand_queries, rank_candidates

BASE_URL = "https://openapi.etsy.com/v3/application"


class EtsyApiError(RuntimeError):
    pass


class EtsyAuthError(EtsyApiError):
    """The API key was rejected (401/403); retrying other keywords won't help."""


class EtsyApi:
    def __init__(
        self,
        api_key: str,
        shared_secret: str | None = None,
        client: httpx.Client | None = None,
        min_interval: float = 0.25,
        fx: FxRates | None = None,
    ):
        # Etsy expects "keystring:shared_secret" in x-api-key; older apps take the keystring.
        key = f"{api_key}:{shared_secret}" if shared_secret else api_key
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=30)
        self._headers = {"x-api-key": key}
        self._min_interval = min_interval
        self._last_call = 0.0
        self._fx = fx

    @property
    def fx(self) -> FxRates:
        """USD exchange rates, loaded on first use (Etsy prices are in the seller's currency)."""
        if self._fx is None:
            self._fx = FxRates()
        return self._fx

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
                raise EtsyAuthError(
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
        return self.search_page(keyword, limit, offset).get("results", [])

    def search_page(self, keyword: str, limit: int = 100, offset: int = 0) -> dict:
        """Raw search response: {"count": total matches, "results": [...]}."""
        return self._get(
            "/listings/active",
            {
                "keywords": keyword,
                "limit": limit,
                "offset": offset,
                "sort_on": "score",
                "sort_order": "desc",
            },
        )

    def listings_batch(self, listing_ids: list[str], buyer_country: str = "US") -> dict[str, dict]:
        """Full listing records, up to 100 per call.

        `BuyerPrice` adds a `buyer_price` block (regular and sale price, discount, shipping
        cost) as a shopper in `buyer_country` would see it, still in the seller's currency.
        """
        out: dict[str, dict] = {}
        for i in range(0, len(listing_ids), 100):
            chunk = listing_ids[i : i + 100]
            data = self._get(
                "/listings/batch",
                {
                    "listing_ids": ",".join(chunk),
                    "includes": "Images,Videos,Shop,BuyerPrice",
                    "buyer_country": buyer_country,
                },
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

    def search_hits(
        self,
        keyword: str,
        top_n: int,
        exclude_digital: bool,
        rank_by: str = "popularity",
        related: list[str] | None = None,
        pool_size: int = 200,
        english_only: bool = True,
    ) -> list[SearchHit]:
        """Top N listings for a keyword.

        rank_by="popularity" (default) searches the keyword plus close variants, keeps
        on-topic English listings, and ranks by favorites then views, which is closer to
        what etsy.com shows. rank_by="relevance" keeps the API's own order for the keyword
        only. See ranking.py.
        """
        if rank_by == "relevance":
            items = self._search_pool(keyword, top_n, exclude_digital)
        else:
            pool: dict[int, dict] = {}
            for query in expand_queries(keyword, related):
                for item in self._search_pool(query, pool_size, exclude_digital=False):
                    pool.setdefault(item["listing_id"], item)
            items = rank_candidates(
                list(pool.values()), keyword, top_n, exclude_digital, english_only
            )
        return [
            SearchHit(
                rank=rank,
                listing_id=str(item["listing_id"]),
                url=canonical_listing_url(item.get("url", "")),
                title=item.get("title"),
                # No price here: prices come from listing_details, converted to USD.
                shop_id=str(item["shop_id"]) if item.get("shop_id") else None,
                api_rank=item.get("_api_rank"),
                matched_query=item.get("_matched_query"),
                rank_method=rank_by,
            )
            for rank, item in enumerate(items, start=1)
        ]

    def _search_pool(self, query: str, size: int, exclude_digital: bool) -> list[dict]:
        """Up to `size` API results for one query, tagged with their API position."""
        out: list[dict] = []
        offset = 0
        while len(out) < size and offset < 1000:
            page = self.search(query, limit=100, offset=offset)
            if not page:
                break
            for item in page:
                offset += 1
                item["_api_rank"] = offset
                item["_matched_query"] = query
                if exclude_digital and item.get("listing_type") == "download":
                    continue
                out.append(item)
        return out[:size]

    def listing_details(self, listing_ids: list[str]) -> dict[str, ListingDetails]:
        raw = self.listings_batch(listing_ids)
        out: dict[str, ListingDetails] = {}
        for lid, item in raw.items():
            shop = item.get("shop") or {}
            media = len(item.get("images") or []) + len(item.get("videos") or [])
            reviews, stars = self.listing_review_stats(lid)
            out[lid] = ListingDetails(
                num_photos_video=media or None,
                reviews=reviews,
                review_star=stars,
                shop_id=str(item["shop_id"]) if item.get("shop_id") else None,
                shop_name=shop.get("shop_name"),
                is_digital=item.get("listing_type") == "download",
                views=item.get("views"),
                num_favorers=item.get("num_favorers"),
                tags=item.get("tags") or [],
                materials=item.get("materials") or [],
                **self._prices(item),
            )
        return out

    def _prices(self, item: dict) -> dict:
        """USD regular/sale price plus the original amount and currency for one listing."""
        bp = item.get("buyer_price") or {}
        regular = money(bp.get("original_price") or item.get("price"))
        sale = None
        if bp.get("has_discount") and bp.get("discounted_price"):
            sale = self.fx.money_to_usd(bp["discounted_price"])
        shipping = bp.get("shipping_cost")
        return {
            "price": self.fx.to_usd(*regular) if regular else None,
            "sale_price": sale,
            "price_original": regular[0] if regular else None,
            "price_currency": regular[1] if regular else None,
            "discount_pct": bp.get("discount_percentage") if sale is not None else None,
            "shipping_cost_usd": self.fx.money_to_usd(shipping) if shipping else None,
            "free_shipping": bp.get("is_free_shipping") if bp else None,
        }

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
