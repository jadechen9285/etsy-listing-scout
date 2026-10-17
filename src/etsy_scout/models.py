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
EXTRA_COLUMNS = ["is_ad", "listing_id", "title", "source", "scraped_at"]
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


class ListingDetails(BaseModel):
    """Fields read from a single listing page or the listing API."""

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


class ListingRow(BaseModel):
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
        data["scraped_at"] = self.scraped_at.strftime("%Y-%m-%d %H:%M:%S")
        return {col: data[col] for col in COLUMNS}
