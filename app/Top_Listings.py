"""Small web UI: `uv run streamlit run app/Top_Listings.py`."""

from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from etsy_scout.browser import BlockedError
from etsy_scout.etsy_api import EtsyApiError
from etsy_scout.export import (
    TooBigForExcel,
    batch_name,
    excel_bytes,
    slugify,
    summary_frame,
    to_dataframe,
)
from etsy_scout.pipeline import (
    MAX_KEYWORDS,
    estimate_api_calls,
    keywords_from_file,
    parse_keywords,
    run_many,
)

CALL_WARNING = 1000  # warn before batches that may use a big share of the daily API quota

load_dotenv()
st.set_page_config(page_title="Etsy Listing Scout", layout="wide")
st.title("Etsy Listing Scout")
st.caption(
    "Top Etsy search results for one or more keywords, in the competitor_listing format, "
    "from the Etsy Open API. Several keywords are combined into one file."
)

has_key = bool(os.getenv("ETSY_API_KEY"))
st.sidebar.markdown(f"**Etsy API key:** {'found' if has_key else 'not set'}")
if not has_key:
    st.warning("Set ETSY_API_KEY in .env to use the default api source (see README).")

# --- inputs (outside a form so the keyword count and call estimate update live) -----
k1, k2 = st.columns([2, 1])
keyword_text = k1.text_area(
    "Keywords (one per line, or comma-separated)",
    placeholder="adhd notebook\nadhd planner\nmagnetic planner",
    height=130,
)
upload = k2.file_uploader(
    "...or upload a keyword list",
    type=["txt", "csv"],
    help=".txt: one keyword per line. .csv: keywords in the first column "
    "(a 'keyword' header is skipped).",
)

c1, c2, c3 = st.columns(3)
top_n = c1.slider("Top N per keyword", 1, 100, 20)
source = c2.selectbox(
    "Data source",
    ["api", "hybrid", "browser"],
    help="api: Etsy Open API (needs ETSY_API_KEY). hybrid/browser are experimental: "
    "Etsy usually blocks automated Chrome.",
)
include_digital = c3.checkbox("Include digital downloads", value=False)
c4, c5 = st.columns([1, 2])
rank_by = c4.selectbox(
    "Rank by",
    ["popularity", "relevance"],
    help="popularity: searches each keyword plus close variants (e.g. notebook -> journal, "
    "planner) and ranks by favorites, then views. Closer to etsy.com. "
    "relevance: the Etsy API's literal keyword-match order.",
)
related_text = c5.text_input(
    "Related keywords (optional, comma-separated, searched with every keyword)",
    placeholder="brain dump pad, focus planner",
)
related = [k.strip() for k in related_text.split(",") if k.strip()]

keywords = parse_keywords(keyword_text)
if upload is not None:
    keywords = parse_keywords(
        "\n".join(keywords + keywords_from_file(upload.name, upload.getvalue()))
    )

too_many = len(keywords) > MAX_KEYWORDS
if keywords:
    calls = estimate_api_calls(keywords, top_n, rank_by, related)
    st.caption(f"**{len(keywords)} keyword(s)** · up to ~{calls:,} Etsy API calls")
    if too_many:
        st.error(f"At most {MAX_KEYWORDS} keywords per batch. Split the list into smaller batches.")
    elif source == "api" and calls > CALL_WARNING:
        st.warning(
            f"This batch may use ~{calls:,} API calls, a large share of Etsy's daily limit. "
            "Consider fewer keywords or a smaller Top N."
        )

run_clicked = st.button("Run", type="primary", disabled=not keywords or too_many)

# --- run --------------------------------------------------------------------------
if run_clicked:
    log = st.status(f"Running {len(keywords)} keyword(s)...", expanded=True)
    try:
        result = run_many(
            keywords,
            top_n=top_n,
            exclude_digital=not include_digital,
            source=source,
            on_progress=log.write,
            rank_by=rank_by,
            related=related,
        )
    except (BlockedError, EtsyApiError, ValueError) as exc:
        log.update(label="Stopped", state="error")
        st.error(str(exc))
        st.stop()
    log.update(
        label=f"Done: {len(result.rows)} listings for {len(result.per_keyword)} keyword(s)",
        state="complete",
        expanded=False,
    )
    st.session_state["result"] = (keywords, to_dataframe(result.rows), result.failed)

# --- results ------------------------------------------------------------------------
if "result" in st.session_state:
    kws, df, failed = st.session_state["result"]
    for kw, err in failed.items():
        st.warning(f"No results for **{kw}**: {err}")

    if df.empty:
        st.info("No listings found.")
        st.stop()

    batch = df["target_keyword"].nunique() > 1
    summary = summary_frame(df) if batch else None
    if batch:
        st.subheader("Per keyword")
        st.dataframe(summary, hide_index=True, use_container_width=True)

    st.subheader("Listings")
    shown = df
    if batch:
        pick = st.multiselect("Filter by keyword", df["target_keyword"].unique().tolist())
        if pick:
            shown = df[df["target_keyword"].isin(pick)]
    st.dataframe(
        shown,
        hide_index=True,
        use_container_width=True,
        column_config={"listing_link": st.column_config.LinkColumn("listing_link")},
    )

    st.caption("Downloads contain every keyword in one file.")
    stem = f"{slugify(batch_name(kws))}_{datetime.now():%Y%m%d_%H%M%S}"
    d1, d2 = st.columns(2)
    d2.download_button("Download CSV", df.to_csv(index=False).encode(), f"{stem}.csv", "text/csv")
    try:
        d1.download_button("Download Excel", excel_bytes(df, summary), f"{stem}.xlsx")
    except TooBigForExcel as exc:
        d1.warning(f"{exc} Use the CSV download.")
