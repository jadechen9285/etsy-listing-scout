"""Small text-to-value helpers for the messy strings Etsy pages show."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?")
_LISTING_URL = re.compile(r"/listing/(\d+)(?:/([^/?#]+))?")


def parse_count(text: str | None) -> int | None:
    """'1,234 sales' -> 1234, '(10.8k)' -> 10800, '2.1M' -> 2100000."""
    if not text:
        return None
    m = _NUMBER.search(text)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    suffix = (m.group(2) or "").lower()
    value *= {"k": 1_000, "m": 1_000_000}.get(suffix, 1)
    return int(round(value))


def parse_price(text: str | None) -> float | None:
    """'$15.49' / 'USD 1,015.00+' / 'Price: $12.39' -> float."""
    if not text:
        return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", text)
    return float(m.group(1).replace(",", "")) if m else None


def parse_rating(text: str | None) -> float | None:
    """'4.9 out of 5 stars' / '4.9' -> 4.9 (only values 0-5 accepted)."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    value = float(m.group(1))
    return value if 0 <= value <= 5 else None


def years_since(when: datetime | int | float | None, now: datetime | None = None) -> float | None:
    """Years between `when` (datetime or unix seconds) and now, rounded to 2 decimals."""
    if when is None:
        return None
    if isinstance(when, int | float):
        when = datetime.fromtimestamp(when, UTC)
    now = now or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return round((now - when).days / 365.25, 2)


def years_since_year(year_text: str | None, now: datetime | None = None) -> float | None:
    """'On Etsy since 2019' -> years since mid-2019 (the page only shows the year)."""
    if not year_text:
        return None
    m = re.search(r"(19|20)\d{2}", year_text)
    if not m:
        return None
    return years_since(datetime(int(m.group(0)), 7, 1, tzinfo=UTC), now)


def listing_id_from_url(url: str) -> str | None:
    m = _LISTING_URL.search(url)
    return m.group(1) if m else None


def canonical_listing_url(url: str) -> str:
    """Drop tracking query strings: keep https://www.etsy.com/listing/<id>/<slug>."""
    m = _LISTING_URL.search(urlsplit(url).path)
    if not m:
        return url
    slug = f"/{m.group(2)}" if m.group(2) else ""
    return f"https://www.etsy.com/listing/{m.group(1)}{slug}"


def iter_json_ld(html_scripts: list[str]):
    """Yield every JSON-LD object (flattening lists and @graph) from raw script bodies."""
    for raw in html_scripts:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                if "@graph" in item:
                    stack.extend(item["@graph"])
                yield item


def ld_type_is(obj: dict, name: str) -> bool:
    t = obj.get("@type")
    return t == name or (isinstance(t, list) and name in t)
