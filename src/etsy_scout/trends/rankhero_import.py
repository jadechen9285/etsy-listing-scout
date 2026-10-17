"""Parse RankHero keyword pages that the user saved from their own browser.

RankHero's Terms of Use forbid bots and scrapers, so this module never fetches
rankhero.com. Open a keyword page (e.g. https://www.rankhero.com/keywords/adhd-planner),
save it with Cmd/Ctrl+S, and point the importer at the saved .html files.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..parsing import iter_json_ld, ld_type_is, parse_count, parse_price
from .analysis import summarize_trend
from .models import CountryShare, KeywordTrend, MonthlySearches

METRIC_LABELS = {
    "Monthly search volume": "monthly_searches",
    "Competition": "competing_listings",
    "Cost per click": "cpc",
    "Keyword difficulty": "keyword_difficulty",
}
_MONTH = re.compile(r"^([A-Z][a-z]+)\s+(\d{4})$")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


class NotARankHeroPage(ValueError):
    pass


def _parse_month(text: str) -> date | None:
    m = _MONTH.match(text.strip())
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y").date()
    except ValueError:
        return None


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _metric_cards(soup: BeautifulSoup) -> dict[str, str]:
    """Label -> value text for the four metric cards at the top of the page."""
    out: dict[str, str] = {}
    for label in METRIC_LABELS:
        node = soup.find(string=lambda t, label=label: t and t.strip() == label)
        if node is None:
            continue
        # The value is the next non-empty text after the label inside the same card.
        for nxt in node.parent.find_all_next(string=True, limit=6):
            value = nxt.strip()
            if value and value != label:
                out[label] = value
                break
    return out


def _country_section(soup: BeautifulSoup, heading: str) -> list[CountryShare]:
    h2 = soup.find(lambda t: t.name in ("h2", "h3") and t.get_text(strip=True) == heading)
    if h2 is None:
        return []
    section = h2.find_parent("section") or h2.parent
    rows: list[CountryShare] = []
    for name_node in section.select("span[title]"):
        row = name_node.parent
        texts = [s.strip() for s in row.find_all(string=True) if s.strip()]
        # texts look like: ["USA", "8,100", "55%"]
        if len(texts) < 2:
            continue
        pct = next((float(m.group(1)) for t in texts if (m := _PCT.search(t))), None)
        value = next((parse_count(t) for t in texts[1:] if "%" not in t), None)
        if value is not None:
            rows.append(CountryShare(country=texts[0], value=value, pct=pct))
    return rows


def _price_bands(soup: BeautifulSoup) -> dict[str, float]:
    bands: dict[str, float] = {}
    for bar in soup.select("[role='progressbar'][aria-label]"):
        label = bar["aria-label"]
        if "$" not in label or ":" not in label:
            continue
        name, _, value = label.rpartition(":")
        if m := _PCT.search(value):
            bands[name.strip().replace("–", "-")] = float(m.group(1))
    return bands


def _monthly_table(soup: BeautifulSoup) -> list[MonthlySearches]:
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "month" not in headers:
            continue
        series: list[MonthlySearches] = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) >= 2 and (month := _parse_month(cells[0])):
                searches = parse_count(cells[1])
                if searches is not None:
                    series.append(MonthlySearches(month=month, searches=searches))
        return sorted(series, key=lambda m: m.month)
    return []


def parse_rankhero_page(html: str) -> KeywordTrend:
    soup = BeautifulSoup(html, "html.parser")
    scripts = [s.string or "" for s in soup.select("script[type='application/ld+json']")]
    ld = list(iter_json_ld(scripts))
    page = next((o for o in ld if ld_type_is(o, "WebPage")), {})
    product = next((o for o in ld if ld_type_is(o, "Product")), {})
    related = next((o for o in ld if ld_type_is(o, "ItemList")), {})

    url = page.get("url") or page.get("@id")
    if not (url and "rankhero.com/keywords/" in url) and "RankHero" not in html[:20000]:
        raise NotARankHeroPage("This does not look like a saved RankHero keyword page.")

    h1 = soup.find("h1")
    keyword = h1.get_text(strip=True) if isinstance(h1, Tag) else None
    if not keyword and url:
        keyword = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
    if not keyword:
        raise NotARankHeroPage("Could not find the keyword on the page.")

    cards = _metric_cards(soup)
    page_text = soup.get_text(" ", strip=True)
    alt = re.search(r"with\s+([\d,]+)\s+listings targeting", page_text)
    median = re.search(r"most priced around \$([\d,.]+)", page_text) or re.search(
        r"median sits at \$([\d,.]+)", page_text
    )
    offers = product.get("offers") or {}
    updated = _parse_date(page.get("dateModified"))
    if updated is None and (m := re.search(r"Updated\s+([A-Z][a-z]{2} \d{1,2}, \d{4})", page_text)):
        updated = _parse_date(m.group(1))

    monthly = _monthly_table(soup)
    difficulty = cards.get("Keyword difficulty")
    return KeywordTrend(
        keyword=keyword,
        source_url=url,
        updated=updated,
        monthly_searches=parse_count(cards.get("Monthly search volume")),
        competing_listings=parse_count(cards.get("Competition")),
        competing_listings_alt=parse_count(alt.group(1)) if alt else None,
        cpc=parse_price(cards.get("Cost per click")),
        keyword_difficulty=parse_count(difficulty) if difficulty else None,
        price_low=parse_price(str(offers.get("lowPrice") or "")),
        price_high=parse_price(str(offers.get("highPrice") or "")),
        price_median=parse_price(median.group(1)) if median else None,
        price_sample_size=offers.get("offerCount"),
        price_bands=_price_bands(soup),
        search_by_country=_country_section(soup, "Search volume by country"),
        competition_by_country=_country_section(soup, "Competition by country"),
        monthly=monthly,
        related_keywords=[
            item["name"] for item in related.get("itemListElement", []) if item.get("name")
        ],
        summary=summarize_trend(monthly),
    )


def import_rankhero_files(paths: list[Path]) -> tuple[list[KeywordTrend], list[str]]:
    """Parse saved pages; return (trends, warnings). Folders are searched for *.html / *.htm."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files += sorted([*p.glob("*.html"), *p.glob("*.htm")])
        else:
            files.append(p)
    trends: list[KeywordTrend] = []
    warnings: list[str] = []
    seen: dict[str, int] = {}
    for f in files:
        try:
            trend = parse_rankhero_page(f.read_text(errors="replace"))
        except NotARankHeroPage as exc:
            warnings.append(f"{f.name}: {exc}")
            continue
        # Keep the most recently updated copy when a keyword was saved twice.
        key = trend.keyword.lower()
        if key in seen:
            old = trends[seen[key]]
            if (trend.updated or date.min) >= (old.updated or date.min):
                trends[seen[key]] = trend
            continue
        seen[key] = len(trends)
        trends.append(trend)
    return trends, warnings
