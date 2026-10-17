"""`etsy-trends`: keyword demand and market-size tracking.

etsy-trends urls "adhd planner" "adhd notebook" --open   open RankHero pages to save
etsy-trends import-rankhero ~/Downloads/rankhero          parse the saved pages
etsy-trends snapshot "adhd planner" "adhd notebook"       Etsy API market snapshot
etsy-trends snapshot                                      re-snapshot every tracked keyword
etsy-trends report                                        workbook from stored history
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from dotenv import load_dotenv

from ..etsy_api import EtsyApi, EtsyApiError
from ..pipeline import NO_KEY_MESSAGE
from . import history
from .analysis import summarize_trend
from .export import (
    SUMMARY_SHEET,
    country_frame,
    monthly_frame,
    price_band_frame,
    snapshot_frame,
    trend_summary_frame,
    write_workbook,
)
from .market_snapshot import take_snapshot
from .rankhero_import import import_rankhero_files

app = typer.Typer(add_completion=False, help=__doc__, no_args_is_help=True)

OutOpt = Annotated[Path, typer.Option(help="Folder for the Excel workbook")]
HistOpt = Annotated[Path, typer.Option(help="Folder for the history CSVs")]


def rankhero_url(keyword: str) -> str:
    slug = "-".join(keyword.lower().split())
    return f"https://www.rankhero.com/keywords/{slug}"


def _keywords(args: list[str] | None, file: Path | None) -> list[str]:
    kws = list(args or [])
    if file:
        kws += [ln.strip() for ln in file.read_text().splitlines() if ln.strip()]
    return list(dict.fromkeys(k for k in kws if not k.startswith("#")))


@app.command()
def urls(
    keywords: Annotated[list[str] | None, typer.Argument()] = None,
    keywords_file: Annotated[Path | None, typer.Option(help="One keyword per line")] = None,
    open_: Annotated[bool, typer.Option("--open", help="Open each page in your browser")] = False,
) -> None:
    """Print (or open) the RankHero page for each keyword so you can save it with Cmd+S."""
    for kw in _keywords(keywords, keywords_file):
        url = rankhero_url(kw)
        typer.echo(url)
        if open_:
            webbrowser.open_new_tab(url)


@app.command("import-rankhero")
def import_rankhero(
    paths: Annotated[list[Path], typer.Argument(help="Saved .html files or folders")],
    out: OutOpt = Path("output"),
    history_dir: HistOpt = history.DEFAULT_DIR,
) -> None:
    """Parse RankHero keyword pages you saved from your browser."""
    trends, warnings = import_rankhero_files(paths)
    for w in warnings:
        typer.secho(f"skipped {w}", fg="yellow", err=True)
    if not trends:
        typer.secho("No RankHero keyword pages found.", fg="red", err=True)
        raise typer.Exit(1)

    monthly = history.merge_monthly(trends, history_dir)
    for t in trends:  # re-label with the full stored series (enables YoY after 24 months)
        t.summary = summarize_trend(history.monthly_series(t.keyword, history_dir)) or t.summary
    history.append_history([history.trend_record(t) for t in trends], history_dir)

    summary = trend_summary_frame(trends)
    kws = {t.keyword.lower() for t in trends}
    path = write_workbook(
        {
            SUMMARY_SHEET: summary,
            "monthly_searches": monthly_frame(monthly[monthly["keyword"].str.lower().isin(kws)]),
            "price_bands": price_band_frame(trends),
            "search_by_country": country_frame(trends, "search"),
            "competition_by_country": country_frame(trends, "competition"),
        },
        out,
        "keyword_trends",
    )
    cols = ["Keyword", "Typical monthly searches", "Competing listings", "Ad cost per click"]
    typer.echo(summary[[*cols, "Trend"]].to_string(index=False))
    typer.secho(f"\nImported {len(trends)} keywords -> {path}", fg="green")


@app.command()
def snapshot(
    keywords: Annotated[list[str] | None, typer.Argument()] = None,
    keywords_file: Annotated[Path | None, typer.Option(help="One keyword per line")] = None,
    sample_size: Annotated[int, typer.Option(min=1, max=500)] = 100,
    include_digital: bool = False,
    out: OutOpt = Path("output"),
    history_dir: HistOpt = history.DEFAULT_DIR,
) -> None:
    """Record Etsy's competing-listing count and price stats for each keyword (Etsy API)."""
    load_dotenv()
    kws = _keywords(keywords, keywords_file)
    if not kws:  # default: every keyword already tracked
        kws = sorted(history.load_history(history_dir)["keyword"].dropna().unique().tolist())
    if not kws:
        raise typer.BadParameter("Give keywords, --keywords-file, or import RankHero pages first.")
    api = EtsyApi.from_env()
    if api is None:
        typer.secho(NO_KEY_MESSAGE, fg="red", err=True)
        raise typer.Exit(1)

    snaps = []
    for kw in kws:
        typer.echo(f"snapshot: {kw}", err=True)
        try:
            snaps.append(take_snapshot(api, kw, sample_size, not include_digital))
        except EtsyApiError as exc:
            typer.secho(str(exc), fg="red", err=True)
            raise typer.Exit(1) from exc
    hist = history.append_history([history.snapshot_record(s) for s in snaps], history_dir)
    df = snapshot_frame(snaps)
    path = write_workbook({"etsy_market_snapshot": df, "history": hist}, out, "market_snapshot")
    cols = ["keyword", "competing_listings", "sample_size", "price_p25", "price_median"]
    typer.echo(df[[*cols, "price_p75"]].to_string(index=False))
    typer.secho(f"\nSaved {len(snaps)} snapshots -> {path}", fg="green")


@app.command()
def report(
    out: OutOpt = Path("output"),
    history_dir: HistOpt = history.DEFAULT_DIR,
) -> None:
    """Write a workbook from everything stored in the history folder."""
    hist = history.load_history(history_dir)
    if hist.empty:
        typer.secho("No history yet. Run import-rankhero or snapshot first.", fg="yellow")
        raise typer.Exit(1)
    monthly_path = history_dir / history.MONTHLY_FILE
    monthly = pd.read_csv(monthly_path) if monthly_path.exists() else pd.DataFrame()
    latest = hist.sort_values("snapshot_date").groupby(["keyword", "source"]).tail(1)
    path = write_workbook(
        {"latest": latest, "history": hist, "monthly_searches": monthly_frame(monthly)},
        out,
        "trend_report",
    )
    typer.secho(f"Report -> {path}", fg="green")


if __name__ == "__main__":
    app()
