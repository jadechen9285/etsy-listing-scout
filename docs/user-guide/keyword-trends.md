# Keyword trends (`etsy-trends`)

`etsy-trends` measures how popular a keyword is and how crowded and expensive its market is, so you can judge a product line before you make it. It fills the `rankhero_search_trend` sheet of the market-research workbook, and adds detail sheets and history charts.

## Where the numbers come from

| Data | Source | How automatic |
|---|---|---|
| Monthly searches, 12-month trend, ad cost per click, keyword difficulty, price bands, country split, related keywords | RankHero keyword pages | **Semi-automatic.** You save each page in your browser and the tool reads the saved file |
| Total competing listings, price min/quartiles/max, price bands, average favorites | Etsy Open API | **Fully automatic** (needs your API key) |
| Trend lines over time | Local history in `data/` | **Automatic.** Every import and snapshot is added |

**Why RankHero is semi-automatic:** Etsy doesn't publish search volume, so third-party estimates are the only source. RankHero's [terms of use](https://www.rankhero.com/terms) forbid "bots, scrapers, or automated tools", so the tool never connects to rankhero.com. You open the pages yourself, which takes about 5 seconds per keyword.

## Workflow

### 1. Open the RankHero pages

```bash
uv run etsy-trends urls "adhd planner" "adhd notebook" "magnetic planner" --open
```

This opens one browser tab per keyword. Leave out `--open` to only print the URLs. For a long list, put one keyword per line in a text file (lines starting with `#` are ignored):

```bash
uv run etsy-trends urls --keywords-file keywords.txt --open
```

### 2. Save each page

In each tab, press **⌘S** (Ctrl+S on Windows), choose **Webpage, HTML Only**, and save it into one folder, for example `~/Downloads/rankhero`. File names don't matter.

### 3. Import the saved pages

```bash
uv run etsy-trends import-rankhero ~/Downloads/rankhero
```

You can pass folders or individual `.html` files. Files that aren't RankHero keyword pages are skipped with a warning. If the same keyword was saved twice, the copy with the newest "Updated" date wins.

The command writes `output/keyword_trends_<timestamp>.xlsx` with these sheets:

| Sheet | Contents |
|---|---|
| `rankhero_search_trend` | the sheet-2 columns (**Keyword, Typical monthly searches, Competing listings, Ad cost per click, Trend**), then keyword difficulty, peak and low month, seasonality ratio, latest vs 12-month average, YoY %, price low/median/high, top search country, data date, source URL, and related keywords. Sorted by search volume. |
| `monthly_searches` | one row per keyword, one column per month |
| `price_bands` | % of listings under $10, $10–$25, $25–$50, $50–$100, and $100+ |
| `search_by_country`, `competition_by_country` | volume and share per country |

It also adds the data to your history (see [History](#history)).

### 4. Take Etsy market snapshots (needs an API key)

```bash
uv run etsy-trends snapshot "adhd planner" "adhd notebook"
uv run etsy-trends snapshot            # no keywords: re-snapshot every keyword in your history
```

For each keyword, this records:
- `competing_listings`: Etsy's total number of active listings matching the keyword (all listing types)
- price stats (min, 25th percentile, median, 75th percentile, max) and price bands for the most relevant listings (100 by default; change it with `--sample-size`)
- `avg_favorites` for those listings, a rough demand signal

By default, digital downloads are left out of the price sample. Add `--include-digital` to keep them.

**Run it on a schedule**, weekly for example, to build trend lines for competition and prices.

### 5. Build a report from history

```bash
uv run etsy-trends report
```

This writes `output/trend_report_<timestamp>.xlsx` with the latest row per keyword and source, the full history, and every stored monthly series.

## How the Trend label is computed

| Label | When |
|---|---|
| `Seasonal: peak Dec, low Jun (2.2x)` | the busiest month of the latest 12 is at least **1.8×** the quietest |
| `Rising +38%` / `Falling -20%` / `Stable (+3%)` | otherwise, comparing the average of the last 3 months with the first 3 (±15% thresholds) |
| `Rising +30% YoY` (plus a season note if seasonal) | once **24 or more months** are stored for the keyword: last 12 months vs the 12 before |
| `No search volume` / `No data` | RankHero has no volume for the keyword |

Why: one RankHero page shows only 12 months, which can't tell a seasonal dip from real decline. "adhd planner", for example, drops every summer and peaks in December. Calling it "Falling" in August would be wrong.

The numeric columns behind the label are also in the sheet: **Last 3 vs first 3 mo %**, **Latest vs 12-mo avg %**, **Seasonality (peak/low)**, and **YoY %**.

**Getting YoY:** every import merges its 12 months into `data/monthly_searches.csv`. Re-import your keywords every few months, and after a year each keyword will have 24+ months and a real year-over-year trend.

## History

| File | One row per | Written by |
|---|---|---|
| `data/keyword_history.csv` | keyword × source × date | `import-rankhero` (source `rankhero`, dated by RankHero's "Updated" date) and `snapshot` (source `etsy_api`, dated today) |
| `data/monthly_searches.csv` | keyword × month | `import-rankhero` |

Running the same import or snapshot twice on the same day replaces that day's row instead of duplicating it. `data/` is git-ignored, so back it up yourself if long-term history matters to you. Every command takes `--history-dir` to use another folder.

## Reading the numbers

- **Typical monthly searches**: RankHero's estimate of Etsy searches. Compare keywords with each other rather than trusting the absolute value.
- **Competing listings**: RankHero's card figure (all countries). The summary sheet also keeps the second figure quoted in RankHero's text, under "Competing listings (summary)". The Etsy API snapshot gives Etsy's own count.
- **Demand vs competition**: searches ÷ competing listings is a quick opportunity ratio. High searches with few listings is the sweet spot.
- **Price bands**: show where most listings sit, so you can price inside the main band or justify a premium.
