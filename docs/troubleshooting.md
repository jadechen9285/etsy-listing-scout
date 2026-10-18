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

## Results don't match what I see on etsy.com

That's expected. The data is live, but etsy.com personalizes results, matches by meaning, and mixes in ads, and the public API can't reproduce that. The default `--rank-by popularity` gets much closer by also searching close variants and ranking by favorites and views. To include specific listings, add the words they use with `--related "brain dump pad"`, or add a synonym group in `src/etsy_scout/ranking.py`. See [How results are ranked](user-guide/top-listings.md#how-results-are-ranked).

## "N keywords is more than the 50 allowed per batch"

Split the list into several batches. The cap protects Etsy's daily API limit; each keyword costs about 10 + 2 × top N calls.

## Some keywords failed in a batch

The other keywords still finished and are in the file. The failed ones are printed as `Failed: '<keyword>': ...` (in the web app, as warnings). This is usually a temporary Etsy error, so rerun just those keywords.

## Two keywords returned the same listings

With the default popularity ranking, keywords whose product nouns are synonyms (e.g. "adhd notebook" and "adhd planner") search the same variants. Use `--rank-by relevance` to compare them on their exact words. See [Several keywords at once](user-guide/top-listings.md#several-keywords-at-once).

## Some columns are empty

| Column | Why | What to do |
|---|---|---|
| `is_best_seller` | the Etsy API doesn't provide the Bestseller badge | expected with `--source api` |
| `on_sales_price_dollar` | the listing isn't on sale | expected |
| `price_dollar` for non-USD sellers | the exchange-rate service (frankfurter.dev) was unreachable; a `could not load exchange rates` warning was printed | rerun later. `price_original` and `price_currency` are still filled |
| `materials` | the seller didn't enter materials | expected; many sellers leave this blank |
| shop columns | the shop lookup failed for that listing; a `warning:` line was printed during the run | rerun later |
| RankHero metric columns | RankHero changed its page layout | see [Contributing → When a page layout changes](developer/contributing.md#when-a-page-layout-changes) |

## `skipped <file>: This does not look like a saved RankHero keyword page`

The file isn't a RankHero keyword page (`rankhero.com/keywords/...`). Save it again with **Webpage, HTML Only**. Some browsers' "Webpage, Single File" (`.mhtml`) format isn't supported.

## Etsy shows a CAPTCHA, or "Bot check was not cleared"

You're using an experimental `hybrid` or `browser` source. Etsy's bot protection usually blocks automated Chrome even after a manual CAPTCHA. Use the default `--source api`.

## `Playwright does not support chromium on mac13`

Only the experimental browser sources need a browser. They use your installed Google Chrome (`BROWSER_CHANNEL=chrome`), so you don't need Playwright's bundled Chromium.
