# Etsy Listing Scout

Give it a keyword and `top_n`. It returns the top N Etsy listings for that keyword and saves them to Excel and CSV, using the same columns as the `competitor_listing` market-research sheet.

```bash
uv run etsy-scout "adhd notebook" --top-n 20
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
uv run streamlit run app/streamlit_app.py
```

Type a keyword, pick Top N, and click **Run**. You get a results table with Excel and CSV download buttons.

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
app/streamlit_app.py web UI
tests/
```
