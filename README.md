# Etsy Listing Scout

Market research for Etsy product lines.

- **`etsy-scout`** finds the top N Etsy listings for one or more keywords, with price, reviews, and shop stats, in the `competitor_listing` sheet format. Several keywords are combined into one CSV and Excel file.
- **`etsy-trends`** tracks keyword demand, competition, and prices over time, in the `rankhero_search_trend` sheet format, with history charts.
- **Web app**: the same features in a browser (Streamlit).

## Quick start

```bash
git clone git@github.com:jadechen9285/etsy-listing-scout.git
cd etsy-listing-scout
uv sync
cp .env.example .env          # add your Etsy API key (see docs/getting-started.md)

uv run etsy-scout "adhd notebook" --top-n 20
uv run etsy-scout "adhd notebook" "magnetic planner" "14k gold filled necklace"   # one combined file
uv run etsy-trends urls "adhd planner" --open      # save the page, then:
uv run etsy-trends import-rankhero ~/Downloads/rankhero
uv run etsy-trends snapshot "adhd planner"
uv run streamlit run app/Top_Listings.py
```

Results go to `output/` as Excel and CSV files. Trend history is kept in `data/`.

## Documentation

| | |
|---|---|
| [Getting started](docs/getting-started.md) | install, Etsy API key, first run |
| [Top listings](docs/user-guide/top-listings.md) | `etsy-scout` options, output columns, data sources |
| [Keyword trends](docs/user-guide/keyword-trends.md) | `etsy-trends` workflow, trend labels, history |
| [Web app](docs/user-guide/web-app.md) | the Streamlit pages |
| [Troubleshooting](docs/troubleshooting.md) | common errors and empty columns |
| [Architecture](docs/developer/architecture.md) | how the code is organised |
| [Contributing](docs/developer/contributing.md) | dev setup, tests, adding features, docs policy |

## Data sources and terms

- **Etsy Open API** is the default source. Follow the [Etsy API Terms of Use](https://www.etsy.com/legal/api).
- **RankHero** data is imported from pages you save in your own browser. Its [terms](https://www.rankhero.com/terms) forbid scrapers, so the tool never fetches rankhero.com.
- **etsy.com browser scraping** is experimental and usually blocked by Etsy's bot protection. The project doesn't try to evade it.
