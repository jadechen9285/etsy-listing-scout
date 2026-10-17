# Top listings (`etsy-scout`)

Give `etsy-scout` a search keyword. It returns the top N Etsy listings for it, with pricing, reviews, and shop stats, in the same columns as the `competitor_listing` sheet of the market-research workbook.

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
| `KEYWORD` | required | The Etsy search keyword. Quote it if it has spaces. |
| `--top-n`, `-n` | `20` | How many listings to return (1–200). |
| `--include-digital` | off | Keep digital downloads. By default only physical items are kept, and the sheet's `search_filter` column says `default exclude digital`. |
| `--source` | `api` | Where the data comes from. See [Data sources](#data-sources). |
| `--out` | `output` | Folder for the Excel and CSV files. |
| `--headful / --headless` | headful | Experimental browser sources only: show or hide the Chrome window. |

Examples:

```bash
uv run etsy-scout "adhd planner" -n 50
uv run etsy-scout "adhd planner" --include-digital
uv run etsy-scout "magnetic planner" --out ~/Desktop/research
```

## Output columns

The first 15 columns match the research sheet exactly, in the same order.

| Column | Meaning | With the default `api` source |
|---|---|---|
| `target_keyword` | the keyword you searched | ✅ |
| `search_filter` | `default exclude digital` or `default include digital` | ✅ |
| `rank` | position in the results (1 = top) | ✅ from the API's relevance order, which is close to etsy.com's order but not identical |
| `listing_link` | listing URL with tracking parameters removed | ✅ |
| `price_dollar` | regular price | ✅ |
| `on_sales_price_dollar` | discounted price when on sale | ❌ empty: the public API doesn't expose sale prices |
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
| `is_ad` | `T` if the result was an ad (browser sources only) |
| `listing_id` | Etsy listing ID |
| `title` | listing title |
| `source` | which source filled the row: `api`, `browser`, or `browser+api` |
| `scraped_at` | when the row was collected (UTC) |

## Data sources

| `--source` | Status | What it does |
|---|---|---|
| `api` | **default, recommended** | Uses only the Etsy Open API. Reliable, and needs your API key. |
| `hybrid` | experimental | Takes rank, sale price, and Bestseller badge from the etsy.com search page, and the rest from the API. |
| `browser` | experimental | Uses only etsy.com pages, with no API. |

The experimental sources open your installed Google Chrome. Etsy's bot protection (DataDome) usually blocks automated browsers, even after you solve the CAPTCHA by hand, so expect these to fail. The project deliberately doesn't try to evade bot detection.

## Tips

- Keep request volumes modest and follow the [Etsy API Terms of Use](https://www.etsy.com/legal/api). The client throttles itself and retries when Etsy says it's busy (HTTP 429).
- Each API run makes about 2 + N calls: one search, one batch lookup, one review lookup per listing, and one call per distinct shop.
- To compare keywords side by side, run once per keyword and combine the CSVs, or paste them into your research workbook.
