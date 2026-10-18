# Web app

The web app does the same things as the command-line tools, in a browser.

```bash
uv run streamlit run app/Top_Listings.py
```

Then open <http://localhost:8501>. Stop it with Ctrl+C in the terminal.

## Top Listings page

1. Type a **Search keyword**.
2. Pick **Top N**, the **Data source** (`api` is recommended; see [data sources](top-listings.md#data-sources)), and whether to **Include digital downloads**.
   Choose **Rank by** (`popularity` is closer to etsy.com; see [how results are ranked](top-listings.md#how-results-are-ranked)), and optionally add **Related keywords**, separated by commas.
3. Click **Run**. Progress messages appear while it works.
4. Review the table (listing links are clickable), then click **Download Excel** or **Download CSV**.

The sidebar shows whether an Etsy API key was found in `.env`.

## Keyword Trends page

The page has three tabs.

### RankHero import

1. Type keywords, separated by commas. Each becomes a link to its RankHero page.
2. Open each link, save the page with **⌘S** ("Webpage, HTML Only"), and drag the saved files onto **Saved RankHero pages**.
3. You get a summary table, a monthly-searches chart, a price-band chart, and a **Download Excel** button. The data is also added to your history.

### Etsy market snapshot

Needs an API key. The keyword box comes pre-filled with every keyword in your history. Pick how many listings to sample for prices and click **Take snapshot**.

### History

- **Monthly searches**: every RankHero series you've imported, merged, as one line per keyword.
- **Snapshots over time**: pick a source and a metric (competing listings, median price, monthly searches, CPC, average favorites) to chart it over time. With a single date so far, you get a bar chart until a second snapshot exists.

All three tabs read and write the same `data/` folder as the `etsy-trends` command, so you can mix the CLI and the web app freely.
