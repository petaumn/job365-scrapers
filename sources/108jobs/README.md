# 108.jobs Scraper — Field Coverage

Source: [108.jobs](https://www.108.jobs) — Lao job board (~160K Facebook followers; Laos #1 job board).

## Field Coverage

| Field | Coverage % | Notes |
|---|:---:|---|
| `title` | ~95% | From `h1.job-title` or `h1`. |
| `companyName` | ~90% | From `.company-name` / `.employer`. JS-rendered names occasionally missed. |
| `location` | ~98% | Free-text city name; defaults to `"Vientiane"` when absent. |
| `province` | ~85% | Canonical slug (e.g. `vientiane-capital`). Omitted when city can't be resolved. |
| `salary` | ~30% | LAK range parsed when listed; USD/THB skipped. |
| `description` | ~95% | Factual summary (≥120 chars) from structured listing facts; server AI-backfills if shorter. |
| `skills` | ~25% | From `.skill` / `.tag` / `.badge` elements. |
| `category` | ~80% | Mapped to 10 canonical Job365 categories; omitted when ambiguous. |
| `type` | ~70% | `FULL_TIME` / `PART_TIME` / `CONTRACT` / `INTERNSHIP`. Always sent. |
| `sourceType` | 100% | `EMPLOYER_DIRECT` when careers page confirmed live; `BOARD` otherwise. |
| `company.website` | ~40% | Employer website when linked from listing. |
| `company.logoUrl` | ~35% | Company logo from listing page. |
| `company.about` | ~20% | Company description when present on listing. |
| `company.facebookUrl` | ~30% | Facebook page when linked (public pages only). |
| `sourceUrl` | 100% | Careers page URL for `EMPLOYER_DIRECT`; 108.jobs permalink for `BOARD`. |

## Canonical category mapping

| 108.jobs terms | Job365 category |
|---|---|
| Software / Developer / IT / Cyber / Data analyst | `Engineering & IT` |
| Banking / Accounting / Audit / Insurance / Finance manager | `Banking & Finance` |
| Sales / Marketing / Brand / Digital marketing | `Sales & Marketing` |
| Admin / HR / Secretary / Receptionist / Legal | `Admin & HR` |
| Manufacturing / Construction / Factory / Quality control | `Manufacturing` |
| Hotel / Hospitality / Tourism / Restaurant | `Hospitality & Tourism` |
| Doctor / Nurse / Medical / Clinic | `Healthcare` |
| NGO / INGO / UN / Development officer | `NGO & Development` |
| Teacher / Education / Lecturer | `Education & Training` |
| Logistics / Supply chain / Warehouse / Procurement | `Logistics & Supply Chain` |
| Ambiguous | _(omitted — server infers from title/description)_ |

## Canonical province slugs

The scraper sends `province` as a slug and `location` as a free-text city name.

| Slug | Covers |
|---|---|
| `vientiane-capital` | Vientiane Capital / ນະຄອນຫຼວວຽງຈັນ |
| `vientiane` | Vientiane Province / ແຂວງວຽງຈັນ |
| `savannakhet` | Savannakhet |
| `luang-prabang` | Luang Prabang |
| `champasak` | Champasak / Pakse |
| `khammouane` | Khammouane |
| `bolikhamsai` | Bolikhamsai |
| `salavan` | Salavan / Saravane |
| `houaphanh` | Houaphanh |
| `oudomxay` | Oudomxay |
| `bokeo` | Bokeo |
| `luang-namtha` | Luang Namtha |
| `xayaboury` | Xayaboury |
| `xieng-khouang` | Xieng Khouang |
| `phongsaly` | Phongsaly |
| `attapeu` | Attapeu |
| `sekong` | Sekong |
| `xaisomboun` | Xaisomboun |

## Run

```bash
export JOB365_SOURCING_TOKEN=...
python -m sources.108jobs.scrape --dry-run --max-pages 3
```

## Notes

- **Origin resolution:** the scraper probes the employer's domain for a careers page on each listing. If found and reachable, `sourceType: EMPLOYER_DIRECT` is sent and `sourceUrl` points to the careers page. Otherwise falls back to `BOARD` with the 108.jobs permalink.
- **Description:** a factual summary is composed from structured fields (company, role, location, salary, skills, bullet facts). No verbatim copy of the board's expressive prose. Server AI-backfills if summary is < 120 chars.
- **Company block:** logo, about, website, Facebook/LinkedIn links are emitted when found on the listing page. These feed shadow company profiles (non-destructive; unclaimed employers only). All assets tagged with `assetSourceUrl`.
- **Salary parsing:** handled by `lib/post.py:parse_salary()`. LAK values only; USD/THB/EUR skipped.
- **Duplicate detection:** HTTP 409 from the Job365 API = already-known `sourceUrl`; scraper logs and skips silently.
- **Rate limiting:** 2.5-second delay between requests.
