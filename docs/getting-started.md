# Getting started

This guide takes you from nothing to your first spreadsheet in about 10 minutes, not counting the wait for Etsy to approve your API key.

## 1. Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and git. uv installs Python 3.12 and every dependency for you.

```bash
git clone git@github.com:jadechen9285/etsy-listing-scout.git
cd etsy-listing-scout
uv sync
```

Check that it worked:

```bash
uv run etsy-scout --help
uv run etsy-trends --help
```

> **Run every command from the project folder.** `uv run` only finds `etsy-scout` and `etsy-trends` inside `etsy-listing-scout/`. To run them from anywhere, add `--directory`:
>
> ```bash
> uv run --directory ~/Desktop/projects/github/etsy-listing-scout etsy-scout "adhd notebook"
> ```

## 2. Get an Etsy API key

Most features read data from the official Etsy Open API, which needs a free key.

1. Sign in to etsy.com. Turn on two-factor authentication under **Settings → Security**; Etsy usually requires it for developer access.
2. Go to <https://www.etsy.com/developers/register> and create an app:
   - **Application name:** anything, for example "Etsy Listing Scout"
   - **Description:** for example, "Personal market-research tool that reads public listing and shop data for keyword searches."
   - **Website URL:** `https://github.com/jadechen9285/etsy-listing-scout`
   - **Who will use it:** "Just myself or colleagues"
3. Wait for approval. New apps can stay **Pending** for anything from minutes to a few days, and every call fails with a 403 until the app is active.
4. Open <https://www.etsy.com/developers/your-apps>, open your app, and copy the **Keystring** and **Shared secret**.

## 3. Add the key to `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```
ETSY_API_KEY=your_keystring
ETSY_SHARED_SECRET=your_shared_secret
```

`.env` is git-ignored, and a pre-commit check blocks private keys, so your key stays on your machine.

## 4. First runs

```bash
# Top 20 listings for a keyword -> output/adhd_notebook_<timestamp>.xlsx and .csv
uv run etsy-scout "adhd notebook" --top-n 20

# Etsy market snapshot for a few keywords
uv run etsy-trends snapshot "adhd planner" "adhd notebook"

# Or use the web app
uv run streamlit run app/Top_Listings.py
```

You don't need the API key for RankHero imports. You can start the [keyword trends](user-guide/keyword-trends.md) workflow while you wait for approval.

## Where files go

| Folder | What's in it | In git? |
|---|---|---|
| `output/` | Excel and CSV files from every run | No |
| `data/` | trend history (`keyword_history.csv`, `monthly_searches.csv`) | No. Back it up if you care about long-term trends |
| `.browser-profile/` | Chrome profile for the experimental browser sources | No |

## Next steps

- [Top listings guide](user-guide/top-listings.md)
- [Keyword trends guide](user-guide/keyword-trends.md)
- [Troubleshooting](troubleshooting.md)
