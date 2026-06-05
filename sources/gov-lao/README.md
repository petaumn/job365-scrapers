# Lao Government Portals Scraper — Field Coverage

Primary source: [National Employment Service Centre (NESC)](https://nesc.gov.la)  
Operated by: Ministry of Labour and Social Welfare (MLSW)  
`sourceType`: `GOV_PORTAL` (platform priority 4 — above `BOARD`)

## Field Coverage

| Field | Coverage % | Notes |
|---|:---:|---|
| `title` | ~95% | Extracted from `h1` / `.job-title`. Missing only on malformed pages. |
| `companyName` | ~85% | Ministry / department name when published. Falls back to `"Government of Laos"`. |
| `location` | ~90% | Province + city when listed. Falls back to `"Laos"`. |
| `province` | ~80% | Mapped to canonical slug via `lib/normalize.canonicalize_province`. |
| `description` | ~80% | Capped at 4,000 chars. Server AI-backfills if < 120 chars. |
| `salary` | ~15% | Government postings rarely publish salary; LAK range parsed when present. |
| `skills` | ~10% | Extracted from tagged skill elements when present. Server enriches. |
| `category` | ~70% | Inferred from title/description via `lib/normalize.infer_category` (10-value set). |
| `type` | ~60% | Inferred from employment-type text. Defaults to `FULL_TIME`. |
| `sourceUrl` | 100% | Always set — canonical nesc.gov.la permalink. |
| `company.website` | ~40% | Ministry website link when published on the listing. |
| `company.logoUrl` | ~30% | Ministry logo when found in the page header. |

## Run

```bash
export JOB365_SOURCING_TOKEN=...
python sources/gov-lao/scrape.py --dry-run --max-pages 3
```

Or for a full run:

```bash
python sources/gov-lao/scrape.py --max-pages 10
```

## Data Quality Notes

- **Salary coverage is low (~15%)** — government jobs in Laos rarely publish salaries publicly. The `no_salary` quality flag will be common for this source; this is expected, not a scraper failure.
- **Description quality varies** — some NESC postings have full job descriptions; others are brief notices. The server's `thin_description` flag will surface entries needing human review.
- **Province canonical rate (~80%)** — covers all 18 Lao provinces in Lao script and English via `lib/normalize.PROVINCE_SLUGS`.
- **sourceType advantage** — `GOV_PORTAL` (priority 4) means these jobs will upgrade any existing `BOARD`-sourced copies of the same listing when deduplication runs.

## Updating Selectors

If the NESC website is redesigned:
1. Run `--dry-run` to see what `_parse_job` extracts.
2. Update CSS selectors in `_get_job_urls` and `_parse_job` in `scrape.py`.
3. Update coverage table above after confirming new selectors.
