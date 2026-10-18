import httpx
import pandas as pd
import pytest
from test_pipeline import fx_handler, handler
from typer.testing import CliRunner

from etsy_scout import cli
from etsy_scout.etsy_api import EtsyApi, EtsyAuthError
from etsy_scout.export import batch_name, excel_bytes, summary_frame, to_dataframe, write_outputs
from etsy_scout.fx import FxRates
from etsy_scout.pipeline import (
    MAX_KEYWORDS,
    BatchResult,
    estimate_api_calls,
    keywords_from_file,
    parse_keywords,
    run,
    run_many,
)


def make_api(calls: list[str] | None = None, fail_query: str | None = None) -> EtsyApi:
    def counting(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        if fail_query and request.url.params.get("keywords") == fail_query:
            return httpx.Response(500, text="boom")
        return handler(request)

    client = httpx.Client(
        base_url="https://openapi.etsy.com/v3/application",
        transport=httpx.MockTransport(counting),
    )
    fx = FxRates(client=httpx.Client(transport=httpx.MockTransport(fx_handler)))
    return EtsyApi("key", "secret", client=client, min_interval=0, fx=fx)


def quiet(_):
    pass


# --- keyword parsing ------------------------------------------------------------------


def test_parse_keywords_splits_dedupes_and_skips_comments():
    text = "adhd notebook, adhd planner\n\n# ideas\n  ADHD   Notebook \nmagnetic planner,"
    assert parse_keywords(text) == ["adhd notebook", "adhd planner", "magnetic planner"]
    assert parse_keywords("   \n# only a comment") == []


def test_keywords_from_csv_and_txt_files():
    csv_data = b"keyword,notes\nadhd notebook,x\nadhd planner,y\n"
    assert keywords_from_file("list.csv", csv_data) == ["adhd notebook", "adhd planner"]
    assert keywords_from_file("list.CSV", b"adhd notebook\n") == ["adhd notebook"]
    assert keywords_from_file("list.txt", b"\xef\xbb\xbfa, b\nc") == ["a", "b", "c"]


def test_estimate_api_calls():
    # popularity: 5 queries x 2 pages + 1 batch + 2 per listing
    assert estimate_api_calls(["adhd notebook"], top_n=10) == 10 + 1 + 20
    assert estimate_api_calls(["adhd notebook"], top_n=10, rank_by="relevance") == 1 + 1 + 20
    assert estimate_api_calls(["a", "b"], top_n=10, rank_by="relevance") == 2 * 22


# --- run_many -------------------------------------------------------------------------


def test_run_many_combines_keywords_and_shares_shop_lookups():
    calls: list[str] = []
    result = run_many(
        ["adhd notebook", "adhd journal"], api=make_api(calls), on_progress=quiet, top_n=5
    )
    assert result.failed == {}
    # "adhd journal" also searches its variants (incl. "adhd notebook"), so it finds 3 too.
    assert result.per_keyword == {"adhd notebook": 3, "adhd journal": 3}
    keywords = [r.target_keyword for r in result.rows]
    assert keywords == ["adhd notebook"] * 3 + ["adhd journal"] * 3
    assert [r.rank for r in result.rows] == [1, 2, 3, 1, 2, 3]  # ranks restart per keyword
    assert {r.rank_method for r in result.rows} == {"popularity"}
    # Every listing is from shop 9: looked up once for the whole batch.
    assert calls.count("/v3/application/shops/9") == 1


def test_run_many_records_a_failing_keyword_and_continues():
    result = run_many(
        ["adhd notebook", "boom"],
        api=make_api(fail_query="boom"),
        on_progress=quiet,
        top_n=5,
        rank_by="relevance",
    )
    assert result.per_keyword == {"adhd notebook": 2}
    assert "boom" in result.failed and "500" in result.failed["boom"]
    assert {r.rank_method for r in result.rows} == {"relevance"}


def test_run_many_stops_on_rejected_key():
    client = httpx.Client(
        base_url="https://x",
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": "inactive"})),
    )
    api = EtsyApi("key", client=client, min_interval=0)
    with pytest.raises(EtsyAuthError):
        run_many(["a", "b"], api=api, on_progress=quiet)


def test_run_many_limits_and_requires_keywords():
    with pytest.raises(ValueError, match="more than"):
        run_many([f"kw {i}" for i in range(MAX_KEYWORDS + 1)], api=make_api(), on_progress=quiet)
    with pytest.raises(ValueError, match="No keywords"):
        run_many(["  ", "# x"], api=make_api(), on_progress=quiet)


def test_website_rank_method_for_browser_hits():
    from etsy_scout.models import ListingDetails, SearchHit, ShopStats
    from etsy_scout.pipeline import build_row

    hit = SearchHit(rank=1, listing_id="9", url="u", rank_method="website")
    row = build_row("kw", "f", hit, ListingDetails(), ShopStats(), "browser")
    assert row.rank_method == "website"


# --- combined export --------------------------------------------------------------------


def test_combined_export_has_all_rows_and_a_summary_sheet(tmp_path):
    result = run_many(["adhd notebook", "adhd journal"], api=make_api(), on_progress=quiet, top_n=5)
    df = to_dataframe(result.rows)
    summary = summary_frame(df)
    assert summary["target_keyword"].tolist() == ["adhd notebook", "adhd journal"]
    assert summary["listings"].tolist() == [3, 3]
    assert summary["rank_method"].tolist() == ["popularity", "popularity"]

    xlsx, csv = write_outputs(
        result.rows, batch_name(["adhd notebook", "adhd journal"]), tmp_path, summary=True
    )
    assert csv.name.startswith("adhd_notebook_and_1_more_")
    assert len(pd.read_csv(csv)) == 6
    sheets = pd.read_excel(xlsx, sheet_name=None)
    assert set(sheets) == {"keyword_summary", "competitor_listing"}
    assert len(sheets["competitor_listing"]) == 6


def test_single_keyword_export_has_no_summary_sheet(tmp_path):
    rows = run("adhd notebook", api=make_api(), on_progress=quiet, top_n=2)
    xlsx, _ = write_outputs(rows, batch_name(["adhd notebook"]), tmp_path)
    assert list(pd.read_excel(xlsx, sheet_name=None)) == ["competitor_listing"]
    assert excel_bytes(to_dataframe(rows))[:2] == b"PK"  # a valid xlsx (zip) file


# --- CLI --------------------------------------------------------------------------------


def test_cli_accepts_several_keywords_and_a_keywords_file(tmp_path, monkeypatch):
    seen: list[list[str]] = []

    def fake_run_many(keywords, **kwargs):
        seen.append(keywords)
        rows = run_many(["adhd notebook"], api=make_api(), on_progress=quiet, top_n=2).rows
        return BatchResult(rows=rows, per_keyword={k: 2 for k in keywords})

    monkeypatch.setattr(cli, "run_many", fake_run_many)
    kw_file = tmp_path / "kws.txt"
    kw_file.write_text("adhd planner\n# skip\nadhd notebook\n")
    out = tmp_path / "out"
    res = CliRunner().invoke(
        cli.app,
        ["adhd notebook", "magnetic planner", "--keywords-file", str(kw_file), "--out", str(out)],
    )
    assert res.exit_code == 0, res.output
    assert seen == [["adhd notebook", "magnetic planner", "adhd planner"]]
    csvs = list(out.glob("*.csv"))
    assert len(csvs) == 1 and csvs[0].name.startswith("adhd_notebook_and_2_more_")


def test_cli_requires_a_keyword():
    res = CliRunner().invoke(cli.app, [])
    assert res.exit_code != 0


# --- Streamlit page -------------------------------------------------------------------


def test_streamlit_page_renders_keyword_inputs():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app/Top_Listings.py", default_timeout=30).run()
    assert not at.exception
    at.text_area[0].input("adhd notebook\nadhd planner, adhd notebook").run()
    assert any("2 keyword(s)" in c.value for c in at.caption)
    assert not at.button[0].disabled


def test_streamlit_blocks_oversized_batches():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app/Top_Listings.py", default_timeout=30).run()
    at.text_area[0].input("\n".join(f"kw {i}" for i in range(MAX_KEYWORDS + 1))).run()
    assert at.button[0].disabled
    assert at.error
