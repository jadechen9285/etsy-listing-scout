"""Command line entry point: `etsy-scout "adhd notebook" --top-n 20`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from .browser import BlockedError
from .export import to_dataframe, write_outputs
from .pipeline import SOURCES, run

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def scout(
    keyword: Annotated[str, typer.Argument(help="Etsy search keyword, e.g. 'adhd notebook'")],
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
) -> None:
    load_dotenv()
    if source not in SOURCES:
        raise typer.BadParameter(f"source must be one of: {', '.join(SOURCES)}")
    try:
        rows = run(
            keyword,
            top_n=top_n,
            exclude_digital=not include_digital,
            source=source,  # type: ignore[arg-type]
            headless=None if headful is None else not headful,
            on_progress=lambda msg: typer.echo(msg, err=True),
        )
    except (BlockedError, ValueError) as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(1) from exc
    if not rows:
        typer.secho("No listings found.", fg="yellow", err=True)
        raise typer.Exit(1)

    xlsx, csv = write_outputs(rows, keyword, out)
    df = to_dataframe(rows)
    preview = df[["rank", "price_dollar", "on_sales_price_dollar", "reviews", "shop_name"]]
    typer.echo(preview.to_string(index=False))
    typer.secho(f"\nSaved {len(rows)} rows:\n  {xlsx}\n  {csv}", fg="green")


if __name__ == "__main__":
    app()
