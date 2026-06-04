# 108.jobs Scraper — Field Coverage

Source: [108.jobs](https://www.108.jobs) — Lao job board.

## Field Coverage

| Field | Coverage % | Notes |
|---|:---:|---|
| `title` | ~95% | Extracted from `h1.job-title` or `h1`. Missing on malformed pages. |
| `companyName` | ~90% | Extracted from `.company-name` or `.employer`. Occasional JS-rendered names missed. |
| `location` | ~98% | Falls back to `"Vientiane"` when not found. |
| `salary` | ~30% | Many posts omit salary. LAK range parsed when present; USD/THB skipped. |
| `description` | ~88% | Capped at 4 000 chars. Server backfills thin descriptions. |
| `skills` | 0% | Not scraped — server extracts from description. |
| `sourceUrl` | 100% | Always set — canonical 108.jobs permalink. |

## Run

```bash
export JOB365_SOURCING_TOKEN=...
python -m sources.108jobs.scrape --dry-run --max-pages 3
```

## Notes

- Province normalisation: Lao and English city names are mapped to canonical
  province names via `PROVINCE_MAP` in `scrape.py`.
- Salary parsing: handled by `lib/post.py:parse_salary()`.
- Duplicate detection: the Job365 API returns HTTP 409 for already-known
  `sourceUrl` — the scraper logs and skips silently.
