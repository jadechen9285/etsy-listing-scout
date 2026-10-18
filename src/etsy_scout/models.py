"""Data shapes shared by the scrapers, the API client, and the exporter."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

# Column order of the `competitor_listing` sheet in the market-research workbook,
# followed by a few extra columns the tool adds.
TEMPLATE_COLUMNS = [
    "target_keyword",
    "search_filter",
    "rank",
    "listing_link",
    "price_dollar",
    "on_sales_price_dollar",
    "num_photos_video",
    "reviews",
    "review_star",
    "is_best_seller",
    "shop_name",
    "shop_age_year",
    "shop_total_sales",
    "shop_total_review",
    "shop_total_product",
]
# Popularity, material, and price-detail columns (from the Etsy API).
LISTING_EXTRA_COLUMNS = [
    "views",
    "num_favorers",
    "tags",
    "materials",
    "price_original",
    "price_currency",
    "discount_pct",
    "shipping_cost_usd",
    "free_shipping",
    "api_rank",
    "matched_query",
]
EXTRA_COLUMNS = [*LISTING_EXTRA_COLUMNS, "is_ad", "listing_id", "title", "source", "scraped_at"]
COLUMNS = TEMPLATE_COLUMNS + EXTRA_COLUMNS


class SearchHit(BaseModel):
    """One card on a search results page, in display order."""

    rank: int
    listing_id: str
    url: str
    title: str | None = None
    is_ad: bool = False
    price: float | None = None
    sale_price: float | None = None
    is_best_seller: bool | None = None
    shop_name: str | None = None
    shop_id: str | None = None
    shop_rating: float | None = None  # stars shown on the card are the shop's average
    api_rank: int | None = None  # position in the Etsy API's own results for matched_query
    matched_query: str | None = None  # which search query found the listing


class ListingExtras(BaseModel):
    """Listing fields beyond the research sheet: popularity, materials, price details."""

    views: int | None = None  # lifetime listing views
    num_favorers: int | None = None  # shoppers who favorited the listing
    tags: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    price_original: float | None = None  # regular price in the seller's currency
    price_currency: str | None = None  # seller's currency, e.g. "GBP"
    discount_pct: float | None = None  # current sale discount, e.g. 25.0
    shipping_cost_usd: float | None = None  # shipping to a US buyer
    free_shipping: bool | None = None


class ListingDetails(ListingExtras):
    """Fields read from a single listing page or the listing API.

    `price` and `sale_price` are in USD.
    """

    price: float | None = None
    sale_price: float | None = None
    num_photos_video: int | None = None
    reviews: int | None = None
    review_star: float | None = None
    is_best_seller: bool | None = None
    shop_name: str | None = None
    shop_id: str | None = None
    shop_url: str | None = None
    is_digital: bool | None = None


class ShopStats(BaseModel):
    shop_name: str | None = None
    shop_age_year: float | None = None
    shop_total_sales: int | None = None
    shop_total_review: int | None = None
    shop_total_product: int | None = None
    shop_rating: float | None = None


class ListingRow(ListingExtras):
    target_keyword: str
    search_filter: str
    rank: int
    listing_link: str
    price_dollar: float | None = None
    on_sales_price_dollar: float | None = None
    num_photos_video: int | None = None
    reviews: int | None = None
    review_star: float | None = None
    is_best_seller: bool | None = None
    shop_name: str | None = None
    shop_age_year: float | None = None
    shop_total_sales: int | None = None
    shop_total_review: int | None = None
    shop_total_product: int | None = None
    api_rank: int | None = None
    matched_query: str | None = None
    is_ad: bool = False
    listing_id: str
    title: str | None = None
    source: str = ""
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_record(self) -> dict:
        """Flatten to the sheet's conventions (T/F booleans, ISO timestamp)."""
        data = self.model_dump()
        if data["is_best_seller"] is not None:
            data["is_best_seller"] = "T" if data["is_best_seller"] else "F"
        data["is_ad"] = "T" if data["is_ad"] else "F"
        if data["free_shipping"] is not None:
            data["free_shipping"] = "T" if data["free_shipping"] else "F"
        data["tags"] = ", ".join(data["tags"]) or None
        data["materials"] = ", ".join(data["materials"]) or None
        data["scraped_at"] = self.scraped_at.strftime("%Y-%m-%d %H:%M:%S")
        return {col: data[col] for col in COLUMNS}
