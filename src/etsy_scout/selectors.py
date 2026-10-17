"""Every CSS selector and text pattern used to read etsy.com pages.

Etsy changes its markup often. When a column comes back empty, fix it here first.
Each entry is a list tried in order; the first match wins.
"""

import re

# --- search results page ------------------------------------------------------
SEARCH_RESULTS_CONTAINER = [
    "[data-search-results-container]",
    "[data-search-results]",
    "ol[data-results-grid-container]",
    "main",
]
SEARCH_CARD = "[data-listing-id]"
CARD_LINK = ["a.listing-link", "a[href*='/listing/']"]
CARD_TITLE = ["h3.v2-listing-card__title", "h3", "h2"]
CARD_CURRENT_PRICE = [".lc-price .currency-value", "p.lc-price .currency-value", ".currency-value"]
CARD_ORIGINAL_PRICE = [".search-collage-promotion-price .currency-value", "s .currency-value"]
CARD_SHOP_NAME = ["[data-shop-name]", ".v2-listing-card__shop p", ".shop-name-with-rating p"]

AD_TEXT = re.compile(r"\bAd (?:by|from) (?:Etsy seller|shop)\b|\bAd by\b", re.I)
AD_URL_HINTS = ("ref=sc_gallery", "ad_id=", "&pro=1&ad")
BESTSELLER_TEXT = re.compile(r"\bBest\s?seller\b", re.I)
SALE_PRICE_TEXT = re.compile(r"Sale Price[:\s]*\D{0,4}(\d[\d,]*\.?\d*)", re.I)
ORIGINAL_PRICE_TEXT = re.compile(r"Original Price[:\s]*\D{0,4}(\d[\d,]*\.?\d*)", re.I)

# --- listing page -------------------------------------------------------------
BUY_BOX = ["[data-buy-box-region]", "#listing-page-cart", "[data-component='listing-page-buy-box']"]
LISTING_PRICE = ["[data-buy-box-region='price'] p", "[data-selector='price-only'] p"]
CAROUSEL_ITEM = [
    "ul[data-carousel-pagination-list] li",
    "[data-carousel-pagination-item]",
    ".listing-page-image-carousel-component li[data-index]",
]
VIDEO = ["[data-carousel-video]", ".listing-page-image-carousel-component video", "video"]
SHOP_LINK = ["a[href*='etsy.com/shop/']", "a[href^='/shop/']"]

LISTING_PRICE_TEXT = re.compile(r"(?:Price|Sale Price)[:\s]*\D{0,4}(\d[\d,]*\.?\d*)", re.I)
ITEM_REVIEWS_TEXT = [
    re.compile(r"Item reviews\s*\(?\s*(\d[\d,.]*\s*[kK]?)\s*\)?", re.I),
    re.compile(r"(\d[\d,.]*\s*[kK]?)\s+reviews? for this item", re.I),
    re.compile(r"Reviews for this item\s*\(?\s*(\d[\d,.]*\s*[kK]?)", re.I),
]
DIGITAL_TEXT = re.compile(r"\bDigital download\b|\bInstant Download\b", re.I)

# --- shop page ----------------------------------------------------------------
SHOP_SALES_TEXT = re.compile(r"(\d[\d,.]*\s*[kK]?)\s+Sales?\b", re.I)
SHOP_SINCE_TEXT = re.compile(r"On Etsy since\s*((?:19|20)\d{2})", re.I)
SHOP_YEARS_TEXT = re.compile(r"(\d+)\s+years? on Etsy", re.I)
SHOP_ITEMS_TEXT = [
    re.compile(r"All items?\s*\(?\s*(\d[\d,]*)\s*\)?", re.I),
    re.compile(r"\bAll\s+(\d[\d,]*)\b"),
    re.compile(r"(\d[\d,]*)\s+items?\b", re.I),
]
SHOP_REVIEWS_TEXT = [
    re.compile(r"out of 5 stars\s*\(\s*(\d[\d,.]*\s*[kK]?)\s*\)", re.I),
    re.compile(r"Reviews\s*\(?\s*(\d[\d,.]*\s*[kK]?)\s*\)", re.I),
    re.compile(r"\((\d[\d,.]*\s*[kK]?)\s*reviews?\)", re.I),
    re.compile(r"(\d[\d,.]*\s*[kK]?)\s+reviews?\b", re.I),
]
SHOP_RATING_TEXT = re.compile(r"(\d\.\d)\s*(?:out of 5|star)", re.I)
