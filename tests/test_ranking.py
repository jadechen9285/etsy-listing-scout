from etsy_scout.ranking import (
    MAX_QUERIES,
    core_terms,
    expand_queries,
    is_on_topic,
    popularity_key,
    rank_candidates,
)


def item(lid, title, favs=0, views=0, tags=(), language="en-US", listing_type="physical", **kw):
    return {
        "listing_id": lid,
        "title": title,
        "tags": list(tags),
        "num_favorers": favs,
        "views": views,
        "language": language,
        "listing_type": listing_type,
        **kw,
    }


def test_expand_queries_swaps_product_noun():
    assert expand_queries("ADHD Notebook") == [
        "adhd notebook",
        "adhd diary",
        "adhd journal",
        "adhd notepad",
        "adhd planner",
    ]
    assert expand_queries("14k gold filled necklace")[1:] == [
        "14k gold filled chain",
        "14k gold filled choker",
        "14k gold filled pendant",
    ]
    assert expand_queries("cat mug")[0] == "cat mug" and "cat tumbler" in expand_queries("cat mug")
    assert expand_queries("lavender soap") == ["lavender soap"]  # no known product noun


def test_related_keywords_come_right_after_the_keyword_and_queries_are_capped():
    queries = expand_queries("adhd notebook", related=["Brain Dump Pad", "adhd notebook"])
    assert queries[:2] == ["adhd notebook", "brain dump pad"]
    assert len(queries) == len(set(queries)) <= MAX_QUERIES


def test_core_terms_drop_product_nouns_and_stopwords():
    assert core_terms("adhd notebook for adults") == {"adhd", "adults"}
    assert core_terms("tote bag for teachers") == {"teachers"}
    assert core_terms("notebook") == set()


def test_on_topic_checks_title_and_tags():
    assert is_on_topic(item(1, "Brain dump notepad", tags=["ADHD gift"]), {"adhd"})
    assert not is_on_topic(item(2, "Weekly planner"), {"adhd"})
    assert is_on_topic(item(3, "Anything"), set())


def test_popularity_order_and_tie_breaks():
    items = [
        item(1, "a", favs=10, views=5, _api_rank=1),
        item(2, "b", favs=50, views=1, _api_rank=9),
        item(3, "c", favs=10, views=99, _api_rank=5),
        item(4, "d", favs=10, views=99, _api_rank=2),
    ]
    assert [i["listing_id"] for i in sorted(items, key=popularity_key)] == [2, 4, 3, 1]


def test_rank_candidates_filters_digital_language_and_topic():
    pool = [
        item(1, "ADHD notebook", favs=5, _matched_query="adhd notebook"),
        item(2, "ADHD printable", favs=99, listing_type="download"),
        item(3, "Cahier TDAH ADHD", favs=80, language="fr"),
        item(4, "Daily planner", favs=70, _matched_query="adhd planner"),
        item(5, "Brain dump pad", favs=60, _matched_query="brain dump pad"),
    ]
    top = rank_candidates(pool, "adhd notebook", top_n=10)
    # 5 is kept: it is checked against the related query that found it.
    assert [i["listing_id"] for i in top] == [5, 1]
    every = rank_candidates(pool, "adhd notebook", 10, exclude_digital=False, english_only=False)
    assert [i["listing_id"] for i in every] == [2, 3, 5, 1]
