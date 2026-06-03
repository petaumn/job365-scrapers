# job365-scrapers

Scraper library for [Job365.ai](https://job365.ai) — Lao-first AI job board.

Each source lives in `sources/<source-name>/scraper.py` and posts normalized jobs
to the Job365 internal API.

---

## Structure

```
job365-scrapers/
├── scripts/
│   └── post.py              # shared API posting helper
├── sources/
│   └── 108jobs/
│       ├── scraper.py       # scraper for 108.jobs
│       └── README.md        # source notes, ToS status, cadence
└── requirements.txt
```

---

## API Contract

**Endpoint:** `POST https://job365.ai/api/internal/jobs/source`
**Auth:** `Authorization: Bearer $JOB365_SOURCING_TOKEN`

### Request body

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | ✅ | Job title |
| `companyName` | string | ✅ | Employer name |
| `companyDomain` | string | — | e.g. `acme.com` |
| `location` | string | ✅ | City or district |
| `province` | string | — | Lao province name |
| `description` | string | ✅ | Min 20 characters |
| `skills` | string[] | — | Tag list |
| `category` | string | — | Job category |
| `salaryMin` | number | — | LAK/month |
| `salaryMax` | number | — | LAK/month |
| `sourceUrl` | string | — | Original listing URL |
| `sourceAttribution` | string | ✅ | e.g. `"108.jobs"` |
| `type` | enum | — | `FULL_TIME` · `PART_TIME` · `CONTRACT` · `TEMPORARY` · `INTERNSHIP` · `FREELANCE` |

### Responses

| Code | Meaning | Action |
|------|---------|--------|
| 201 | Created | Log the returned `id`/`slug` |
| 409 | Near-duplicate (last 30 days) | Do **not** retry — log returned id |
| 401 | Bad token | Alert ops team immediately |
| 422 | Validation error | Fix payload, re-post |

---

## Running a scraper

```bash
# set token
export JOB365_SOURCING_TOKEN=your_token_here

# run
python sources/108jobs/scraper.py
```

---

## Adding a new source

1. Create `sources/<source-name>/`
2. Add `scraper.py` — must call `scripts/post.py:post_job(payload)` for each listing
3. Add `README.md` documenting: ToS status, robots.txt check, cadence, data quirks
4. Open a PR — CI will lint + dry-run

---

## Guidelines

- Respect `robots.txt` and rate limits (≥2s between requests)
- `User-Agent: Job365-Scraper/1.0 (+https://job365.ai)`
- Do **not** scrape Facebook or LinkedIn aggressively — ToS violation; flag to ops
- Skip 409 responses — they are not errors
- Lao + English output preferred; always pass both when available
- Never commit tokens; read from env vars only
