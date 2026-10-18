"""Top Etsy listings for one or more keywords, saved as one Excel + CSV file.

etsy-scout "adhd notebook"
etsy-scout "adhd notebook" "adhd planner" "magnetic planner" -n 10
etsy-scout --keywords-file keywords.txt
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from .browser import BlockedError
from .etsy_api import EtsyApiError
from .export import batch_name, summary_frame, to_dataframe, write_outputs
from .pipeline import (
    MAX_KEYWORDS,
    RANK_BY,
    SOURCES,
    estimate_api_calls,
    keywords_from_file,
    parse_keywords,
    run_many,
)

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def scout(
    keywords: Annotated[
        list[str] | None,
        typer.Argument(help="One or more Etsy search keywords, e.g. 'adhd notebook'"),
    ] = None,
    keywords_file: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Text file with one keyword per line (or a .csv whose first column holds them)",
        ),
    ] = None,
    top_n: Annotated[int, typer.Option("--top-n", "-n", min=1, max=200)] = 20,
    include_digital: Annotated[
        bool, typer.Option("--include-digital", help="Keep digital downloads in results")
    ] = False,
    source: Annotated[
        str, typer.Option(help="api (default) | hybrid, browser (experimental; see README)")
    ] = "api",
    headful: Annotated[
        bool | None,
        typer.Option(
            "--headful/--headless",
            help="Experimental sources: show Chrome (default)",
        ),
    ] = None,
    out: Annotated[Path, typer.Option(help="Output folder")] = Path("output"),
    rank_by: Annotated[
        str,
        typer.Option(
            help="popularity (default): keyword + close variants, ranked by favorites/views, "
            "closer to etsy.com | relevance: the API's literal-match order"
        ),
    ] = "popularity",
    related: Annotated[
        list[str] | None,
        typer.Option(help="Extra keyword to search too (repeatable; popularity ranking only)"),
    ] = None,
    pool_size: Annotated[
        int, typer.Option(min=20, max=1000, help="API results pooled per query before ranking")
    ] = 200,
    any_language: Annotated[
        bool, typer.Option("--any-language", help="Keep non-English listings")
    ] = False,
) -> None:
    load_dotenv()
    if source not in SOURCES:
        raise typer.BadParameter(f"source must be one of: {', '.join(SOURCES)}")
    if rank_by not in RANK_BY:
        raise typer.BadParameter(f"rank-by must be one of: {', '.join(RANK_BY)}")
    kws = parse_keywords("\n".join(keywords or []))
    if keywords_file:
        kws = parse_keywords(
            "\n".join(kws + keywords_from_file(keywords_file.name, keywords_file.read_bytes()))
        )
    if not kws:
        raise typer.BadParameter("Give at least one keyword, or --keywords-file.")
    if len(kws) > MAX_KEYWORDS:
        typer.secho(
            f"{len(kws)} keywords is more than the {MAX_KEYWORDS} allowed per batch. "
            "Split the list into smaller batches.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)
    if len(kws) > 1 and source == "api":
        calls = estimate_api_calls(kws, top_n, rank_by, related, pool_size)
        typer.echo(f"{len(kws)} keywords, up to ~{calls:,} Etsy API calls.", err=True)

    try:
        result = run_many(
            kws,
            top_n=top_n,
            exclude_digital=not include_digital,
            source=source,  # type: ignore[arg-type]
            headless=None if headful is None else not headful,
            on_progress=lambda msg: typer.echo(msg, err=True),
            rank_by=rank_by,  # type: ignore[arg-type]
            related=related,
            pool_size=pool_size,
            english_only=not any_language,
        )
    except (BlockedError, EtsyApiError, ValueError) as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(1) from exc
    for kw, err in result.failed.items():
        typer.secho(f"Failed: {kw!r}: {err}", fg="yellow", err=True)
    if not result.rows:
        typer.secho("No listings found.", fg="yellow", err=True)
        raise typer.Exit(1)

    batch = len(kws) > 1
    xlsx, csv = write_outputs(result.rows, batch_name(kws), out, summary=batch)
    df = to_dataframe(result.rows)
    if batch:
        cols = ["target_keyword", "listings", "median_price_dollar", "median_num_favorers"]
        typer.echo(summary_frame(df)[cols].to_string(index=False))
    else:
        cols = ["rank", "price_dollar", "on_sales_price_dollar", "reviews", "shop_name"]
        typer.echo(df[cols].to_string(index=False))
    files = "\n".join(f"  {p}" for p in (xlsx, csv) if p)
    typer.secho(
        f"\nSaved {len(result.rows)} rows for {len(result.per_keyword)} keyword(s):\n{files}",
        fg="green",
    )
    if xlsx is None:
        typer.secho("Too many rows for Excel; only the CSV was written.", fg="yellow")


if __name__ == "__main__":
    app()
