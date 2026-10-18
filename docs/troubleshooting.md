# Troubleshooting

## `error: Failed to spawn: etsy-scout` (or `etsy-trends`)

You ran the command outside the project folder. Either `cd` into it first:

```bash
cd ~/Desktop/projects/github/etsy-listing-scout
uv run etsy-trends --help
```

or point uv at it from anywhere:

```bash
uv run --directory ~/Desktop/projects/github/etsy-listing-scout etsy-trends --help
```

If it still fails inside the folder, run `uv sync` to reinstall the commands.

## `ModuleNotFoundError: No module named 'src'` (in a notebook)

Import the installed package by name: `from etsy_scout.export import to_dataframe`, not `from src.etsy_scout...` or `from .export ...`. Also check that the notebook uses this project's `.venv` kernel. See [Contributing → Notebooks](developer/contributing.md#notebooks).

## `No Etsy API key found`

`.env` is missing or has no `ETSY_API_KEY`. See [Getting started → Add the key](getting-started.md#3-add-the-key-to-env). The file must sit in the project folder and be named exactly `.env`.

## `Etsy rejected the API key (403 ... not found or not active ...)`

1. **The app isn't approved yet.** Check <https://www.etsy.com/developers/your-apps>. Calls fail until the app is active, which can take days.
2. **Wrong values.** `ETSY_API_KEY` must be the **Keystring** and `ETSY_SHARED_SECRET` the **Shared secret**, with no quotes or spaces.
3. **No two-factor authentication** on your Etsy account can keep the app inactive.

## Etsy says it's busy (HTTP 429)

You hit Etsy's rate limit. The client waits and retries automatically, so lower `--top-n` or `--sample-size` if it keeps happening.

## Some columns are empty

| Column | Why | What to do |
|---|---|---|
| `on_sales_price_dollar`, `is_best_seller` | the Etsy API doesn't provide sale prices or the Bestseller badge | expected with `--source api` |
| shop columns | the shop lookup failed for that listing; a `warning:` line was printed during the run | rerun later |
| RankHero metric columns | RankHero changed its page layout | see [Contributing → When a page layout changes](developer/contributing.md#when-a-page-layout-changes) |

## `skipped <file>: This does not look like a saved RankHero keyword page`

The file isn't a RankHero keyword page (`rankhero.com/keywords/...`). Save it again with **Webpage, HTML Only**. Some browsers' "Webpage, Single File" (`.mhtml`) format isn't supported.

## Etsy shows a CAPTCHA, or "Bot check was not cleared"

You're using an experimental `hybrid` or `browser` source. Etsy's bot protection usually blocks automated Chrome even after a manual CAPTCHA. Use the default `--source api`.

## `Playwright does not support chromium on mac13`

Only the experimental browser sources need a browser. They use your installed Google Chrome (`BROWSER_CHANNEL=chrome`), so you don't need Playwright's bundled Chromium.
