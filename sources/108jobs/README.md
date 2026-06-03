# sources/108jobs — 108.jobs Scraper

Scrapes public job listings from [108.jobs](https://108.jobs) and submits them to Job365 via `POST /api/internal/jobs/source`.

## Source details
| Field | Value |
|-------|-------|
| Source | 108.jobs (Laos public job aggregator) |
| ToS status | Public API, ToS-friendly |
| robots.txt | Respected |
| Rate limit | 0.5s between source calls, 0.3s between POSTs |
| Attribution | `sourceAttribution: "108.jobs"` |

## Requirements
Standard library only — no `pip install` needed. Python 3.8+.

## Auth
Set `JOB365_SOURCING_TOKEN` in environment before running.

## Usage
```bash
# Full run (all jobs)
python3 scraper.py

# Dry run (fetch + normalise, no POSTs)
python3 scraper.py --dry-run

# Limit to first N jobs
python3 scraper.py --limit 50

# Start from page N (resume after interruption)
python3 scraper.py --page-start 5
```

## Output
`run_log_YYYYMMDD_HHMMSS.json` written next to the script:
```json
{
  "stats": { "submitted": 159, "duplicate": 0, "error": 6, "skipped": 0 },
  "jobs": [{ "id": "...", "slug": "...", "title": "..." }],
  "source": "108.jobs"
}
```

## Response handling
| HTTP status | Meaning | Action |
|-------------|---------|--------|
| 201 | Created | Logged as submitted |
| 409 | Near-duplicate (last 30d) | Skip, do not retry |
| Other | Error | Logged, counted in stats |

## Normalisation
- HTML stripped from descriptions
- Category mapped from 108.jobs `jobFunctionId`
- Province extracted from location string (Lao province names → Job365 province enum)
- Job type: `jobTypeId` → `FULL_TIME / PART_TIME / CONTRACT / TEMPORARY / INTERNSHIP / FREELANCE`
- Salary passed as-is if present (LAK/month)
- Thin descriptions (< 80 chars) get a structured fallback from education/experience/level metadata

## Performance (first run, 2026-06-03)
- 159 jobs submitted, 6 errors, 0 duplicates
- ~8 minutes for full run of ~165 listings
