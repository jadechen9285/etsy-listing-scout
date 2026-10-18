# Top listings (`etsy-scout`)

Give `etsy-scout` one or more search keywords. It returns the top N Etsy listings for each, with pricing, reviews, and shop stats, in the same columns as the `competitor_listing` sheet of the market-research workbook. Several keywords are combined into **one** CSV and Excel file.

## Quick start

```bash
uv run etsy-scout "adhd notebook"
```

This writes two files and prints a short preview:

```
output/adhd_notebook_20261017_141205.xlsx   (sheet: competitor_listing)
output/adhd_notebook_20261017_141205.csv
```

## Options

| Option | Default | What it does |
|---|---|---|
| `KEYWORDS...` | required* | One or more Etsy search keywords. Quote each one that has spaces. |
| `--keywords-file` | none | A text file with one keyword per line, or a `.csv` with keywords in the first column. Can be combined with `KEYWORDS`. *Either keywords or this file is required. |
| `--top-n`, `-n` | `20` | How many listings to return per keyword (1–200). |
| `--include-digital` | off | Keep digital downloads. By default only physical items are kept, and the sheet's `search_filter` column says `default exclude digital`. |
| `--source` | `api` | Where the data comes from. See [Data sources](#data-sources). |
| `--out` | `output` | Folder for the Excel and CSV files. |
| `--rank-by` | `popularity` | `popularity`: search the keyword plus close variants and rank by favorites, then views, which is closer to etsy.com. `relevance`: the Etsy API's own keyword-match order. See [How results are ranked](#how-results-are-ranked). |
| `--related` | none | Another keyword to search as well (repeatable), e.g. `--related "brain dump pad"`. Popularity ranking only. |
| `--pool-size` | `200` | API results collected per query before ranking (20–1000). Larger pools find more listings but cost more API calls. |
| `--any-language` | off | Keep listings that aren't in English. By default only English listings are kept, as a US shopper would mostly see. |
| `--headful / --headless` | headful | Experimental browser sources only: show or hide the Chrome window. |

Examples:

```bash
uv run etsy-scout "adhd planner" -n 50
uv run etsy-scout "adhd planner" --include-digital
uv run etsy-scout "magnetic planner" --out ~/Desktop/research
uv run etsy-scout "adhd notebook" --related "brain dump pad" --related "focus planner"
uv run etsy-scout "adhd notebook" --rank-by relevance     # the API's raw order
```

## Output columns

The first 15 columns match the research sheet exactly, in the same order.

| Column | Meaning | With the default `api` source |
|---|---|---|
| `target_keyword` | the keyword you searched | ✅ |
| `search_filter` | `default exclude digital` or `default include digital` | ✅ |
| `rank` | position in the results (1 = top) | ✅ by popularity across the keyword and its variants (see [How results are ranked](#how-results-are-ranked)) |
| `listing_link` | listing URL with tracking parameters removed | ✅ |
| `price_dollar` | regular price in **USD** | ✅ converted from the seller's currency (see [Prices and currency](#prices-and-currency)) |
| `on_sales_price_dollar` | sale price in **USD**, when the listing is discounted | ✅ empty when not on sale |
| `num_photos_video` | number of photos plus videos | ✅ |
| `reviews` | reviews for this listing | ✅ |
| `review_star` | the shop's average rating (the stars shown on Etsy search cards) | ✅ |
| `is_best_seller` | `T` if the listing has the Bestseller badge | ❌ empty: the API has no badge data |
| `shop_name` | shop name | ✅ |
| `shop_age_year` | years since the shop opened | ✅ |
| `shop_total_sales` | shop's total sales | ✅ |
| `shop_total_review` | shop's total reviews | ✅ |
| `shop_total_product` | shop's active listings | ✅ |

These extra columns come after them:

| Column | Meaning |
|---|---|
| `views` | lifetime views of the listing |
| `num_favorers` | shoppers who favorited the listing, a strong interest signal |
| `tags` | the seller's search tags (up to 13), comma-separated |
| `materials` | seller-entered materials, comma-separated. Often empty, but valuable for physical products such as jewelry |
| `price_original` | regular price in the seller's own currency |
| `price_currency` | the seller's currency, e.g. `GBP` |
| `discount_pct` | the current sale discount, e.g. `25` |
| `shipping_cost_usd` | shipping cost to a US buyer, in USD (empty when free or unknown) |
| `free_shipping` | `T` if shipping to the US is free |
| `api_rank` | the listing's position in the Etsy API's own results for `matched_query` |
| `matched_query` | which search query found the listing, e.g. `adhd notepad` |
| `rank_method` | how `rank` was produced: `popularity` or `relevance` (Etsy API, see [`--rank-by`](#how-results-are-ranked)), or `website` (etsy.com page order, experimental browser sources) |
| `is_ad` | `T` if the result was an ad (browser sources only) |
| `listing_id` | Etsy listing ID |
| `title` | listing title |
| `source` | which source filled the row: `api`, `browser`, or `browser+api` |
| `scraped_at` | when the row was collected (UTC) |

## Several keywords at once

Pass several keywords, a keyword file, or both. Every keyword gets its own top N, and all rows go into one combined file:

```bash
uv run etsy-scout "adhd notebook" "magnetic planner" "14k gold filled necklace" -n 10
uv run etsy-scout --keywords-file keywords.txt
```

`keywords.txt` holds one keyword per line, or comma-separated. Blank lines and lines starting with `#` are ignored, and duplicates (ignoring case) are removed:

```
# stationery
adhd notebook, magnetic planner
# jewelry
14k gold filled necklace
```

The output is `output/<first keyword>_and_<N-1>_more_<timestamp>.csv` and `.xlsx`.
- The **CSV** has every listing row. Filter or pivot on `target_keyword`; `rank` restarts at 1 for each keyword.
- The **Excel** file has the same rows in `competitor_listing`, plus a `keyword_summary` sheet with one row per keyword: listings, rank method, median/min/max price, share on sale, and median favorites, reviews, and shop sales.

**Limits**
- At most **50 keywords** per batch. Each keyword costs about 10 + 2 × top N Etsy API calls with popularity ranking, and Etsy limits calls per day, so the CLI and web app show an estimate before running. Shops shared between keywords are looked up only once.
- Up to 50 × 200 = 10,000 rows, well within Excel's limit. If a result were ever too big for Excel, only the CSV is written.
- If one keyword fails (for example, a temporary Etsy error), it's reported and the others still finish. A rejected API key stops the batch.

**Tip:** with popularity ranking, keywords whose product nouns are synonyms ("adhd notebook" and "adhd planner") search the same variants and can return the same top N. To compare such keywords on their own words, use `--rank-by relevance`.

## How results are ranked

**Why API results differ from etsy.com:** the data isn't outdated (the API is live). The two searches work differently:

| | Etsy API | etsy.com search |
|---|---|---|
| Matching | literal keyword match on title and tags | by meaning: "adhd notebook" also shows ADHD notepads, planners, and journals |
| Ranking | text relevance only, with no popularity signal | popularity, buyer behaviour, listing quality, recency, and ads |
| Personalized | no | yes (location, history, language) |

With the API's own order, the top results for "adhd notebook" were brand-new listings with 0 views (a median of 1 favorite in the top 20), plus non-English and digital listings. The listings a shopper saw at the top of etsy.com didn't contain the words "adhd notebook" at all.

**What `--rank-by popularity` (the default) does:**
1. **Searches close variants too.** The product noun is swapped for synonyms: "adhd notebook" also searches "adhd diary", "adhd journal", "adhd notepad", and "adhd planner". Your `--related` keywords come right after the original keyword, and at most 6 queries are searched in total.
2. **Keeps on-topic listings:** they must be physical (unless `--include-digital`) and in English (unless `--any-language`), and mention every core word of the query that found them (for "adhd notebook" that's "adhd") in the title or tags.
3. **Ranks by popularity:** most favorites first, then most views, then the API's own order.

The result looks much more like what shoppers see: the top 20 for "adhd notebook" went from a median of 1 favorite to 234. It's still an approximation, because etsy.com personalizes results and mixes in ads, so an exact match isn't possible with the public API. `api_rank` and `matched_query` show where each result came from.

The synonym groups live in `PRODUCT_SYNONYMS` in `src/etsy_scout/ranking.py`. Add a group when you research a new product line; jewelry, mugs, stickers, prints, and bags are already covered.

## Prices and currency

Etsy returns every price in the **seller's own currency**. A UK shop's `11.99` is £11.99, not $11.99. To make prices comparable, the tool:

1. asks Etsy for the price a **US shopper** sees (the `BuyerPrice` data), which includes the regular price, any sale price and discount, and shipping to the US
2. converts these amounts to USD with the day's European Central Bank reference rates from [frankfurter.dev](https://frankfurter.dev), which is free and needs no key. Rates are fetched once per run.
3. keeps the unconverted amount in `price_original` and `price_currency`, so you can check any conversion

If the rate service is unreachable, USD prices stay correct for US sellers and are left empty for others, and a warning is printed.

## Data sources

| `--source` | Status | What it does |
|---|---|---|
| `api` | **default, recommended** | Uses only the Etsy Open API. Reliable, and needs your API key. |
| `hybrid` | experimental | Takes rank, sale price, and Bestseller badge from the etsy.com search page, and the rest from the API. |
| `browser` | experimental | Uses only etsy.com pages, with no API. |

The experimental sources open your installed Google Chrome. Etsy's bot protection (DataDome) usually blocks automated browsers, even after you solve the CAPTCHA by hand, so expect these to fail. The project deliberately doesn't try to evade bot detection.

## Tips

- Keep request volumes modest and follow the [Etsy API Terms of Use](https://www.etsy.com/legal/api). The client throttles itself and retries when Etsy says it's busy (HTTP 429).
- Each run with the default popularity ranking makes about 10 + 2N API calls: 2 search calls per query (about 5 queries), one batch lookup, one review lookup per listing, and one call per distinct shop, plus one call for exchange rates. `--rank-by relevance` needs only 1 search call.
- To explore the raw API data yourself, open the walkthrough notebook `notebooks/01_etsy_api_walkthrough.ipynb`.
- To compare keywords side by side, run once per keyword and combine the CSVs, or paste them into your research workbook.
