# Etsy Listing Scout: notes for Claude

Python 3.12 project managed with **uv**. Package `etsy_scout` (in `src/`) with the CLIs `etsy-scout` and `etsy-trends`, and a Streamlit app in `app/`.

## Commands

```bash
uv sync
uv run pytest
uv run ruff check . --fix && uv run ruff format .
uv run pre-commit run --all-files
uv run streamlit run app/Top_Listings.py
uv run jupyter lab            # experiments live in notebooks/
```

Add dependencies with `uv add` / `uv add --dev`, never pip. Notebooks import the installed package (`from etsy_scout... import`), never `src.` or relative imports.

## Rules

- **Documentation is part of every change.** Any new feature, command, option, output column, app page, error message, or env var must update `docs/` in the same commit: the user guide, troubleshooting, architecture, and getting started as relevant, plus the index in `docs/README.md` and the root `README.md` for new tools. The full checklist is in `docs/developer/contributing.md#documentation`.
- **Version control:** commit at meaningful milestones with descriptive messages and push to `origin main`. pre-commit hooks must pass. Never use `--no-verify`.
- **Compliant data access:** use official APIs first. Don't scrape sites whose terms forbid automation (RankHero: user-saved pages only), and don't add bot-detection evasion (Etsy DataDome).
- **Public repo:** test fixtures are hand-written imitations of page structure with made-up numbers. Never commit real pages saved from Etsy or RankHero, `.env`, `data/`, or `output/`.
- **Template columns** (`models.TEMPLATE_COLUMNS`, `trends.models.TREND_TEMPLATE_COLUMNS`) mirror the user's research workbook. Append new columns after them, and never reorder or rename them.
- Keep `parse_*` and analysis functions pure (HTML or JSON in, models out). Tests never hit the network.
