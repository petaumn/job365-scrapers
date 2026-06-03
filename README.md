# job365-scrapers

Sourcing scrapers for [Job365.ai](https://job365.ai) — Laos's Lao-first job board.

Each source lives in `sources/<source-name>/` and is independently runnable.

## Structure
```
sources/
  108jobs/        ← 108.jobs public aggregator (Laos)
  <next-source>/  ← Gov portals, banks, INGOs (coming)
```

## Auth
All scrapers read `JOB365_SOURCING_TOKEN` from the environment.
Tokens are managed in `~/.openclaw/.env` — never commit token values.

## Running a scraper
```bash
export JOB365_SOURCING_TOKEN=<your-token>
python3 sources/108jobs/scraper.py --dry-run   # validate without posting
python3 sources/108jobs/scraper.py             # full run
```

## Adding a new source
1. Create `sources/<name>/scraper.py`
2. Add `sources/<name>/README.md` (source URL, ToS status, rate limits, output schema)
3. Open a PR — CI will lint + dry-run

## Maintainers
- Ops agent: openclaw / job365ai session
- Platform: Peta Nantharath (petaumn)
