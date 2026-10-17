"""Keyword demand and market-size page of the Streamlit app."""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from etsy_scout.etsy_api import EtsyApi, EtsyApiError
from etsy_scout.trends import history
from etsy_scout.trends.analysis import summarize_trend
from etsy_scout.trends.cli import rankhero_url
from etsy_scout.trends.export import (
    SUMMARY_SHEET,
    country_frame,
    monthly_frame,
    price_band_frame,
    snapshot_frame,
    trend_summary_frame,
    workbook_bytes,
)
from etsy_scout.trends.market_snapshot import take_snapshot
from etsy_scout.trends.rankhero_import import NotARankHeroPage, parse_rankhero_page

load_dotenv()
st.set_page_config(page_title="Keyword Trends", layout="wide")
st.title("Keyword Trends")

tab_import, tab_snapshot, tab_history = st.tabs(
    ["RankHero import", "Etsy market snapshot", "History"]
)

# --- RankHero import -----------------------------------------------------------
with tab_import:
    st.markdown(
        "RankHero does not allow scrapers, so this step is manual: open each keyword page, "
        "save it with **Cmd+S** (Webpage, HTML only), then drop the files here."
    )
    kw_text = st.text_input("Keywords to look up (comma-separated)", key="rh_kws")
    for kw in [k.strip() for k in kw_text.split(",") if k.strip()]:
        st.markdown(f"- [{kw}]({rankhero_url(kw)})")

    files = st.file_uploader(
        "Saved RankHero pages", type=["html", "htm"], accept_multiple_files=True
    )
    if files:
        trends, skipped = [], []
        for f in files:
            try:
                trends.append(parse_rankhero_page(f.getvalue().decode("utf-8", "replace")))
            except NotARankHeroPage as exc:
                skipped.append(f"{f.name}: {exc}")
        for s in skipped:
            st.warning(f"Skipped {s}")
        if trends:
            monthly = history.merge_monthly(trends)
            for t in trends:
                t.summary = summarize_trend(history.monthly_series(t.keyword)) or t.summary
            history.append_history([history.trend_record(t) for t in trends])

            summary = trend_summary_frame(trends)
            st.subheader("Summary")
            st.dataframe(summary, hide_index=True, use_container_width=True)

            kws = {t.keyword.lower() for t in trends}
            mine_raw = monthly[monthly["keyword"].str.lower().isin(kws)]
            mine = mine_raw.copy()
            mine["month"] = pd.to_datetime(mine["month"])
            st.subheader("Monthly searches")
            st.line_chart(mine.pivot_table(index="month", columns="keyword", values="searches"))

            bands = price_band_frame(trends).set_index("keyword")
            if not bands.empty:
                st.subheader("Share of listings by price band (%)")
                st.bar_chart(bands.T)

            st.download_button(
                "Download Excel",
                workbook_bytes(
                    {
                        SUMMARY_SHEET: summary,
                        "monthly_searches": monthly_frame(mine_raw),
                        "price_bands": price_band_frame(trends),
                        "search_by_country": country_frame(trends, "search"),
                        "competition_by_country": country_frame(trends, "competition"),
                    }
                ),
                f"keyword_trends_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            )

# --- Etsy API snapshot -----------------------------------------------------------
with tab_snapshot:
    has_key = bool(os.getenv("ETSY_API_KEY"))
    st.markdown(
        "Etsy's own numbers for each keyword: total competing listings and the price spread of "
        "the most relevant listings. Run it regularly to build a trend line."
    )
    if not has_key:
        st.warning("Set ETSY_API_KEY in .env to take snapshots (see README).")
    tracked = sorted(history.load_history()["keyword"].dropna().unique().tolist())
    snap_text = st.text_area("Keywords (one per line)", value="\n".join(tracked), height=150)
    c1, c2 = st.columns(2)
    sample = c1.slider("Listings sampled for prices", 20, 300, 100, step=20)
    incl_digital = c2.checkbox("Include digital downloads", value=False)
    if st.button("Take snapshot", type="primary", disabled=not has_key):
        kws = [k.strip() for k in snap_text.splitlines() if k.strip()]
        api = EtsyApi.from_env()
        snaps = []
        progress = st.progress(0.0)
        try:
            for i, kw in enumerate(kws, start=1):
                snaps.append(take_snapshot(api, kw, sample, not incl_digital))
                progress.progress(i / len(kws), text=kw)
        except EtsyApiError as exc:
            st.error(str(exc))
        if snaps:
            history.append_history([history.snapshot_record(s) for s in snaps])
            st.dataframe(snapshot_frame(snaps), hide_index=True, use_container_width=True)

# --- History ---------------------------------------------------------------------
with tab_history:
    monthly_path = history.DEFAULT_DIR / history.MONTHLY_FILE
    if monthly_path.exists():
        monthly = pd.read_csv(monthly_path, parse_dates=["month"])
        st.subheader("Monthly searches (RankHero, all imports merged)")
        st.line_chart(monthly.pivot_table(index="month", columns="keyword", values="searches"))

    hist = history.load_history()
    if hist.empty:
        st.info("No history yet. Import RankHero pages or take a snapshot first.")
    else:
        st.subheader("Snapshots over time")
        hist["snapshot_date"] = pd.to_datetime(hist["snapshot_date"])
        source = st.radio("Source", sorted(hist["source"].unique()), horizontal=True)
        metric = st.selectbox(
            "Metric",
            ["competing_listings", "price_median", "monthly_searches", "cpc", "avg_favorites"],
        )
        view = hist[hist["source"] == source]
        chart = view.pivot_table(index="snapshot_date", columns="keyword", values=metric)
        if chart.dropna(how="all").empty:
            st.info(f"No {metric} values for {source} yet.")
        elif len(chart) < 2:
            st.info("Only one snapshot date so far. Run again on a later day to see a trend line.")
            st.bar_chart(chart.T)
        else:
            st.line_chart(chart)
        st.dataframe(
            view.sort_values("snapshot_date", ascending=False),
            hide_index=True,
            use_container_width=True,
        )
