# Contributing

## Dev setup

```bash
git clone git@github.com:jadechen9285/etsy-listing-scout.git
cd etsy-listing-scout
uv sync                      # Python 3.12, runtime and dev dependencies
uv run pre-commit install    # run lint and format on every commit
cp .env.example .env         # optional: Etsy API key for live runs
```

Manage dependencies only with uv, so `uv.lock` stays in sync. The pre-commit `uv-lock` hook checks it.

```bash
uv add some-package           # runtime dependency
uv add --dev some-package     # dev-only dependency
```

## Everyday commands

```bash
uv run pytest                        # tests (no network access)
uv run ruff check src tests app notebooks/[0-9]*.ipynb --fix   # lint
uv run ruff format src tests app notebooks/[0-9]*.ipynb        # format
uv run pre-commit run --all-files    # every hook
uv run streamlit run app/Top_Listings.py
uv run jupyter lab
```

## Notebooks

**New to the codebase? Start with [`notebooks/01_etsy_api_walkthrough.ipynb`](../../notebooks/01_etsy_api_walkthrough.ipynb).** It walks through the Etsy API one call at a time (search, listing, prices and currency, popularity and materials, shop, reviews), then the converters and the full pipeline.

Put experiments in `notebooks/`. JupyterLab is a dev dependency, so `uv sync` installs it. Committed tutorial notebooks are numbered (`01_...`) and saved **with outputs cleared**.

```bash
uv run jupyter lab            # or open the .ipynb in VS Code
```

In VS Code, pick the **`.venv` kernel of this project** (`etsy-listing-scout (3.12)`).

`uv sync` installs the package in editable mode, so import it by its package name. Never use `src.` or relative imports in a notebook:

```python
from etsy_scout.pipeline import run
from etsy_scout.export import to_dataframe, write_outputs
from etsy_scout.trends.rankhero_import import parse_rankhero_page
```

| Wrong | Why it fails |
|---|---|
| `from src.etsy_scout.export import ...` | `src/` is a source folder, not a package, and the notebook's working directory is `notebooks/` |
| `from .export import ...` | relative imports only work inside a package, not in a notebook |

Tips:
- The notebook runs from `notebooks/`, so relative paths start there. Use `Path("..") / "output"` for the project's output folder. `load_dotenv()` still finds the project's `.env` by searching parent folders.
- Changes in `src/` reach the notebook automatically after a kernel restart. To pick them up without restarting, run `%load_ext autoreload` and `%autoreload 2` in the first cell.
- Clear outputs before committing a notebook, so API data and large outputs don't end up in this public repo.
- ruff also lints and formats `.ipynb` files. Run it on specific paths (`uv run ruff check src tests app notebooks/01_*.ipynb`) so it doesn't rewrite personal scratch notebooks.

## pre-commit

pre-commit runs these on every commit: trailing whitespace, end-of-file, YAML/TOML checks, a large-file check, a merge-conflict check, private-key detection, ruff lint and format, and `uv lock --check`. If a hook rewrites a file, stage it and commit again.

## Tests

- Tests never touch the network. The API is mocked with `httpx.MockTransport` (see `tests/test_pipeline.py`), and pages are parsed from `tests/fixtures/`.
- **Fixtures are hand-written.** Don't commit pages saved from Etsy, RankHero, or any other site, because this repo is public and that content belongs to them. Write a small HTML file that copies the page's *structure* with made-up numbers (see `tests/fixtures/rankhero_sample.html`).
- To check a parser against a real page, save the page outside the repo (or in the git-ignored `output/`) and run the parser on it locally.

## Adding a feature

1. **Pick the data source compliantly.** Use an official API if there is one. Read the site's terms before writing any scraper. If they forbid automation, build a user-driven import instead, as RankHero does.
2. **Put the logic in `src/etsy_scout/`**, with pure parse and analysis functions and thin I/O wrappers. A new tool gets its own subpackage, like `trends/`, plus a `[project.scripts]` entry in `pyproject.toml`.
3. **Add tests** with hand-written fixtures and mocked HTTP.
4. **Wire up the UI** if it helps. Add a page as `app/pages/<N>_<Name>.py`, calling the package functions.
5. **Document it in the same change.** See [Documentation](#documentation).
6. **Commit at a meaningful milestone**, with a message that says what changed and why, ending with any co-author line. Push to `main` (or open a PR if you're collaborating).

## Documentation

Docs live in `docs/` and are part of the definition of done. A feature or change isn't finished until its docs are updated in the same commit or PR.

| You changed... | Update |
|---|---|
| a new command, app, or page | add a guide under `docs/user-guide/`, link it from `docs/README.md` and the root `README.md` |
| an option, default, or output column | the matching user guide (the options and columns tables) |
| a new error message or known failure | `docs/troubleshooting.md` |
| a new module, data source, or data flow | `docs/developer/architecture.md` (modules table, diagram, data flow) |
| setup, dependencies, env vars | `docs/getting-started.md` and `.env.example` |
| a dev workflow (tests, hooks, release) | this file |

Writing style:
- Write for a user who has never seen the code. Start each guide with what the tool does and a copy-pasteable quick start.
- Every command in the docs must actually run. Copy them from a terminal you just ran.
- Use tables for options and columns, and explain *why* when behaviour might surprise someone (empty columns, seasonal labels, compliance limits).
- Keep the root `README.md` short: an overview, a quick start, and links into `docs/`.

## When a page layout changes

Websites change their HTML. When a column suddenly comes back empty:

- **etsy.com (experimental sources):** set `ETSY_SCOUT_DUMP_DIR=/tmp/etsy-pages` and rerun to save the raw pages. Update `src/etsy_scout/selectors.py`, update the fixture to match the new structure, and run the tests.
- **RankHero:** save a fresh keyword page and run `parse_rankhero_page` on it. Fix `trends/rankhero_import.py` (it reads JSON-LD first, then the cards, tables, and `aria-label`s), then update `tests/fixtures/rankhero_sample.html`.
