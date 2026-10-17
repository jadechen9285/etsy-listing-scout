# Etsy Listing Scout

Give it a keyword and `top_n`. It finds the top N Etsy search results and saves them as Excel and CSV, with the same columns as the `competitor_listing` market-research sheet.

Work in progress. Full setup and usage notes are coming.

```bash
uv sync
uv run etsy-scout "adhd notebook" --top-n 20
```
