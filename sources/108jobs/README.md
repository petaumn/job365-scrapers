# Source: 108.jobs

**URL:** https://www.108.jobs  
**ToS status:** Public listing aggregator — reuse permitted for non-commercial indexing; verify before scale-up  
**robots.txt:** Checked 2026-06-03 — scraping allowed for job detail pages  
**Cadence:** Once per day (cron, 03:00 Vientiane time)  
**Target:** All Lao-location listings, up to 50/run

## Data notes

- Titles and descriptions often in Lao only — scraper attempts to preserve both where present
- Salary rarely listed; omit rather than guess
- `province` field: map from city name using `PROVINCE_MAP` in scraper.py
- Company domain: not reliably available; omit if absent

## Known quirks

- Pagination via `?page=N` — stop when page returns < 5 listings
- Some listings are placement-agency posts — `companyName` may be the agency; flag with `sourceAttribution: "108.jobs"`
- Job type rarely stated — default to `FULL_TIME` only when title clearly implies it (e.g. "ພະນັກງານ Full-Time")
