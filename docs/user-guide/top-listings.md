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
| `is_ad` | `T` if the result was an ad (browser sources only) |
| `listing_id` | Etsy listing ID |
| `title` | listing title |
| `source` | which source filled the row: `api`, `browser`, or `browser+api` |
| `scraped_at` | when the row was collected (UTC) |

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
- Each API run makes about 2 + 2N calls: one search, one batch lookup, one review lookup per listing, and one call per distinct shop (plus one call for exchange rates).
- To explore the raw API data yourself, open the walkthrough notebook `notebooks/01_etsy_api_walkthrough.ipynb`.
- To compare keywords side by side, run once per keyword and combine the CSVs, or paste them into your research workbook.
