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
uv run ruff check . --fix            # lint
uv run ruff format .                 # format
uv run pre-commit run --all-files    # every hook
uv run streamlit run app/Top_Listings.py
```

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
