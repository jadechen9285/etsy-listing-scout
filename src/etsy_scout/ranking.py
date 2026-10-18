"""Rank API search results the way shoppers see them.

The Etsy API's `sort_on=score` is a literal keyword match with no popularity signal: its
top results are often brand-new listings with no views, or listings in other languages.
etsy.com instead matches by meaning (a search for "adhd notebook" also shows ADHD
notepads, planners, and journals) and ranks by popularity and buyer behaviour.

This module approximates the website with public data only:
1. search the keyword plus close variants (synonyms of its product noun)
2. keep listings that are on topic (contain every core term), physical, and in English
3. rank by popularity: favorites, then views

All functions are pure: they take raw API listing dicts and return plain values.
"""

from __future__ import annotations

import re

MAX_QUERIES = 6

# Interchangeable product nouns. Extend this when you research a new product line:
# each group is searched together, so "gold necklace" also searches "gold pendant".
PRODUCT_SYNONYMS: list[set[str]] = [
    {"notebook", "journal", "notepad", "planner", "diary"},
    {"necklace", "pendant", "choker", "chain"},
    {"earrings", "studs", "hoops"},
    {"bracelet", "bangle", "cuff"},
    {"ring", "band"},
    {"mug", "cup", "tumbler"},
    {"sticker", "decal"},
    {"print", "poster", "wall art"},
    {"tote", "tote bag", "bag"},
]
STOPWORDS = {"a", "an", "and", "the", "for", "of", "with", "in", "on", "to", "by", "set"}

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _synonym_group(keyword: str) -> tuple[str, set[str]] | None:
    """(product noun found in the keyword, its synonym group), longest match first."""
    text = f" {' '.join(_words(keyword))} "
    best = None
    for group in PRODUCT_SYNONYMS:
        for noun in group:
            if f" {noun} " in text and (best is None or len(noun) > len(best[0])):
                best = (noun, group)
    return best


def _normalize(text: str) -> str:
    return " ".join(_words(text)) or text.strip().lower()


def expand_queries(keyword: str, related: list[str] | None = None) -> list[str]:
    """Queries to search: the keyword, then `related`, then product-noun synonym variants.

    "adhd notebook" -> ["adhd notebook", "adhd diary", "adhd journal", "adhd notepad",
    "adhd planner"]. Deduplicated and capped at MAX_QUERIES.
    """
    base = _normalize(keyword)
    queries = [base, *(_normalize(r) for r in related or [])]
    if found := _synonym_group(base):
        noun, group = found
        for alt in sorted(group - {noun}):
            queries.append(f" {base} ".replace(f" {noun} ", f" {alt} ", 1).strip())
    return list(dict.fromkeys(q for q in queries if q))[:MAX_QUERIES]


def core_terms(keyword: str) -> set[str]:
    """Words that every result must mention: the keyword minus stopwords and product nouns."""
    product_words = {w for group in PRODUCT_SYNONYMS for noun in group for w in noun.split()}
    return {w for w in _words(keyword) if w not in STOPWORDS and w not in product_words}


def is_on_topic(item: dict, core: set[str]) -> bool:
    if not core:
        return True
    text = " ".join([item.get("title") or "", *(item.get("tags") or [])]).lower()
    found = set(_words(text))
    return core <= found


def is_english(item: dict) -> bool:
    lang = (item.get("language") or "en").lower()
    return lang.startswith("en")


def popularity_key(item: dict) -> tuple:
    """Most favorited first, then most viewed, then the API's own order."""
    return (
        -(item.get("num_favorers") or 0),
        -(item.get("views") or 0),
        item.get("_api_rank", 10**9),
    )


def rank_candidates(
    pool: list[dict],
    keyword: str,
    top_n: int,
    exclude_digital: bool = True,
    english_only: bool = True,
) -> list[dict]:
    """Filter a merged search pool and return the top N by popularity.

    Each item is checked against the core terms of the query that found it
    (`_matched_query`), so results from user-supplied related keywords are kept.
    """
    kept = [
        item
        for item in pool
        if not (exclude_digital and item.get("listing_type") == "download")
        and (not english_only or is_english(item))
        and is_on_topic(item, core_terms(item.get("_matched_query") or keyword))
    ]
    return sorted(kept, key=popularity_key)[:top_n]
