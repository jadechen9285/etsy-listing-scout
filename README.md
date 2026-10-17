# Etsy Listing Scout

Market research for Etsy product lines, with two tools:

- **`etsy-scout`** finds the top N listings for a keyword and saves them in the `competitor_listing` sheet format (price, sale price, reviews, shop stats, and more).
- **`etsy-trends`** tracks keyword demand and market size over time, using the `rankhero_search_trend` sheet format (monthly searches, competing listings, CPC, and trend), plus price bands and history charts.

```bash
uv run etsy-scout "adhd notebook" --top-n 20
uv run etsy-trends import-rankhero ~/Downloads/rankhero
uv run etsy-trends snapshot "adhd planner" "adhd notebook"
```

## Setup

Requires [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 for you.

```bash
git clone git@github.com:jadechen9285/etsy-listing-scout.git
cd etsy-listing-scout
uv sync
uv run pre-commit install
cp .env.example .env   # then add your Etsy API key
```

### Etsy API key

1. Sign in at <https://www.etsy.com/developers/your-apps> and choose **Create a New App**.
2. Once the app is approved, copy its **Keystring** and **Shared secret** into `.env`:

   ```
   ETSY_API_KEY=your_keystring
   ETSY_SHARED_SECRET=your_shared_secret
   ```

The tool only calls public endpoints that need just this key, so no OAuth sign-in is involved.

## Usage

### CLI

```bash
uv run etsy-scout "adhd notebook"                    # top 20, physical items only
uv run etsy-scout "adhd planner" -n 50 --include-digital
uv run etsy-scout "magnetic planner" --out ~/Desktop/research
```

Each run writes `output/<keyword>_<timestamp>.xlsx` (sheet `competitor_listing`) and a `.csv` copy.

### Web UI

```bash
uv run streamlit run app/Top_Listings.py
```

- **Top Listings**: type a keyword, pick Top N, and click **Run**. You get a results table with Excel and CSV download buttons.
- **Keyword Trends**: drop in saved RankHero pages, take Etsy API snapshots, and chart history.

## Keyword trends (`etsy-trends`)

Etsy doesn't publish search volume, so demand numbers come from RankHero. Market size and prices come straight from the Etsy API.

| Data | Source | How automatic |
|---|---|---|
| Monthly searches, 12-month trend, CPC, keyword difficulty, price bands, country split, related keywords | RankHero keyword pages | **Semi-automatic.** [RankHero's terms](https://www.rankhero.com/terms) forbid bots and scrapers, so you save each page in your own browser and the tool parses it. Nothing is fetched from rankhero.com |
| Competing-listing count, price min/quartiles/max, price bands, average favorites | Etsy Open API | **Fully automatic** (needs your API key) |
| Trend lines over time | Local history in `data/` (git-ignored) | **Automatic.** Every import and snapshot is added to the history |

### Workflow

```bash
# 1. Open the RankHero page for each keyword in your browser
uv run etsy-trends urls "adhd planner" "adhd notebook" "magnetic planner" --open
#    ...then save each one with Cmd+S ("Webpage, HTML Only") into one folder.

# 2. Parse the saved pages into a workbook and add them to the history
uv run etsy-trends import-rankhero ~/Downloads/rankhero

# 3. Snapshot Etsy's own numbers (run weekly; with no keywords it re-snapshots every tracked keyword)
uv run etsy-trends snapshot "adhd planner" "adhd notebook"
uv run etsy-trends snapshot

# 4. Build a workbook from all stored history
uv run etsy-trends report
```

You can also pass `--keywords-file keywords.txt` (one keyword per line) to `urls` and `snapshot`.

`import-rankhero` writes `output/keyword_trends_<timestamp>.xlsx` with these sheets:
- `rankhero_search_trend`: the sheet-2 columns (Keyword, Typical monthly searches, Competing listings, Ad cost per click, Trend), followed by difficulty, peak and low month, seasonality, price range, top country, and related keywords
- `monthly_searches`, `price_bands`, `search_by_country`, `competition_by_country`

### How the trend label is computed

A single RankHero page shows only 12 months, which can't separate seasonality from real growth. The label works like this:
- If the busiest month is at least 1.8x the quietest, the keyword is labelled **Seasonal: peak Dec, low Jun (2.2x)** instead of falsely "falling" during its off-season.
- Otherwise the label is **Rising / Falling / Stable**, comparing the last 3 months with the first 3 (±15% thresholds).
- Monthly series from every import are merged in `data/monthly_searches.csv`. Once a keyword has 24 or more months stored, the label switches to a true **year-over-year** change, such as "Rising +30% YoY". Re-import your keywords every few months to get there.

## Output columns

The first 15 columns match the research sheet, in the same order.

| column | how it is filled (api source) |
|---|---|
| target_keyword, search_filter | your input (`default exclude digital` unless `--include-digital`) |
| rank | position in the API's relevance-sorted search results |
| listing_link | listing URL with tracking parameters removed |
| price_dollar | listing price |
| on_sales_price_dollar | *empty*: the public API does not expose sale prices |
| num_photos_video | number of images plus videos |
| reviews | number of reviews for this listing |
| review_star | shop's average rating (the stars shown on Etsy search cards) |
| is_best_seller | *empty*: the API has no Bestseller badge |
| shop_name | shop name |
| shop_age_year | years since the shop opened |
| shop_total_sales, shop_total_review, shop_total_product | shop totals for sales, reviews, and active listings |

These extra columns are added after them: `is_ad`, `listing_id`, `title`, `source`, `scraped_at`.

## Data sources

| `--source` | status | what it does |
|---|---|---|
| `api` | **default** | Uses only the Etsy Open API v3. Reliable. Ranks follow the API's relevance order, which is close to etsy.com's order but not identical. |
| `hybrid` | experimental | Takes ranks, sale prices, and Bestseller badges from the etsy.com search page, and the other columns from the API. |
| `browser` | experimental | Uses only etsy.com pages, with no API. |

The experimental sources drive your installed Google Chrome with Playwright. Etsy protects its site with DataDome, which usually blocks automated browsers even after you solve the CAPTCHA by hand. Expect these sources to fail. This project does not try to evade bot detection. If Etsy changes its markup, all page selectors live in `src/etsy_scout/selectors.py`. Set `ETSY_SCOUT_DUMP_DIR=/some/dir` to save the raw pages a run loads.

Please follow the [Etsy API Terms of Use](https://www.etsy.com/legal/api). Keep request volumes modest. The client throttles its own calls and retries when it gets HTTP 429.

## Development

```bash
uv run pytest            # tests use saved HTML fixtures and a mocked API
uv run ruff check .
uv run pre-commit run --all-files
```

Project layout:

```
src/etsy_scout/
  etsy_api.py        Etsy Open API v3 client
  pipeline.py        keyword -> ranked rows (merges sources)
  export.py          Excel / CSV writer
  cli.py             `etsy-scout` command
  browser.py         Playwright session (experimental sources)
  search_scraper.py, listing_scraper.py, shop_scraper.py, selectors.py
  trends/            etsy-trends: RankHero import, API snapshots, history, analysis
app/Top_Listings.py  web UI (plus app/pages/1_Keyword_Trends.py)
tests/
```
