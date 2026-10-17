"""Small web UI: `uv run streamlit run app/streamlit_app.py`."""

from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from etsy_scout.browser import BlockedError
from etsy_scout.export import excel_bytes, slugify, to_dataframe
from etsy_scout.pipeline import run

load_dotenv()
st.set_page_config(page_title="Etsy Listing Scout", layout="wide")
st.title("Etsy Listing Scout")
st.caption(
    "Top Etsy search results for a keyword, in the competitor_listing format. "
    "If Etsy shows a verification check, solve it in the Chrome window that opens."
)

has_key = bool(os.getenv("ETSY_API_KEY"))
with st.form("search"):
    keyword = st.text_input("Search keyword", placeholder="adhd notebook")
    c1, c2, c3 = st.columns(3)
    top_n = c1.slider("Top N", 1, 100, 20)
    source = c2.selectbox(
        "Data source",
        ["auto", "browser", "api"],
        help="auto: etsy.com ranking, filled from the API when ETSY_API_KEY is set.",
    )
    include_digital = c3.checkbox("Include digital downloads", value=False)
    submitted = st.form_submit_button("Run", type="primary")

st.sidebar.markdown(f"**Etsy API key:** {'found' if has_key else 'not set'}")

if submitted and keyword.strip():
    log = st.status("Running...", expanded=True)
    try:
        rows = run(
            keyword.strip(),
            top_n=top_n,
            exclude_digital=not include_digital,
            source=source,
            on_progress=log.write,
        )
    except (BlockedError, ValueError) as exc:
        log.update(label="Stopped", state="error")
        st.error(str(exc))
        st.stop()
    log.update(label=f"Done: {len(rows)} listings", state="complete", expanded=False)
    st.session_state["result"] = (keyword.strip(), to_dataframe(rows))

if "result" in st.session_state:
    kw, df = st.session_state["result"]
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={"listing_link": st.column_config.LinkColumn("listing_link")},
    )
    stem = f"{slugify(kw)}_{datetime.now():%Y%m%d_%H%M%S}"
    d1, d2 = st.columns(2)
    d1.download_button("Download Excel", excel_bytes(df), f"{stem}.xlsx")
    d2.download_button("Download CSV", df.to_csv(index=False).encode(), f"{stem}.csv", "text/csv")
