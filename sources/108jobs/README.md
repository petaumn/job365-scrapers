# 108.jobs — Source Coverage

Source: [108.jobs](https://www.108.jobs) — Laos #1 job board (160K+ Facebook followers).  
ToS status: ✅ Public listings, no login required. Rate-limit: 2.5 s/request.  
Last checked: 2026-06-04.

## Field Coverage

_Based on a sample of ~200 live listings (June 2026)._

| Field | Coverage | Notes |
|---|:---:|---|
| `title` | ~95% | `h1.job-title` → `h1` fallback. Missing only on malformed pages. |
| `companyName` | ~90% | `.company-name` → `[class*=employer]` fallback. JS-rendered names occasionally missed. |
| `location` | ~98% | Falls back to `"Laos"` when absent. |
| `description` | ~88% | Full body text, capped at 4 000 chars. Server backfills when thin (< 120 chars). |
| `salary` | ~30% | LAK ranges parsed by `lib.normalize.parse_salary`. USD/THB dropped. |
| `skills` | 0% | No reliable tag selector found — server extracts from description. |
| `sourceUrl` | 100% | Canonical 108.jobs permalink always set. |
| `province` | ~70% | Derived from `location` via `lib.normalize.canonicalize_province`. |
| `category` | ~55% | Inferred from title + description via `lib.normalize.infer_category` (10 canonical values). |
| `type` | ~45% | Inferred from title + description via `lib.normalize.infer_type`; defaults to `FULL_TIME`. |

**Median description length:** ~620 characters (full-text mode, pre-truncation).

### Quality score distribution (last 50 posted)

| Score range | % of jobs |
|---|:---:|
| 80–100 (auto-PUBLISHED) | ~42% |
| 60–79 (auto-PUBLISHED) | ~31% |
| < 60 (PENDING\_REVIEW) | ~27% |

**Primary quality gap:** `no_salary` flag (~70% of posts). Next step: improve salary XPath selectors against the 108.jobs DOM.

## Run

```bash
export JOB365_BASE_URL=https://job365.ai
export JOB365_SOURCING_TOKEN=<token>
python -m sources.108jobs.scrape [--dry-run] [--max-pages 5]
```

## Module layout

```
sources/108jobs/
├─ scrape.py   # fetch 108.jobs listings → post to Job365 API
└─ README.md   # this file
```

Shared helpers in `lib/`:

| Module | Exports |
|---|---|
| `lib/normalize.py` | `parse_salary`, `canonicalize_province`, `infer_category`, `infer_type` |
| `lib/post.py` | `post_job`, `post_batch` |
| `lib/config.py` | `BASE_URL`, `TOKEN`, `ENDPOINT` |
