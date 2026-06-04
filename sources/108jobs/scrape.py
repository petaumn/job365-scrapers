"""
sources/108jobs/scrape.py — Scraper for 108.jobs (Lao job board).

Fetches job listings from 108.jobs and posts them to the Job365 sourcing API
via lib/post.py. All normalization (salary, province, category, type) is
handled by lib/normalize.py.

Run:
    export JOB365_SOURCING_TOKEN=...
    python -m sources.108jobs.scrape [--dry-run] [--max-pages 3]
"""
import re
import sys
import time
import logging
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.post import post_batch
from lib.normalize import parse_salary, canonicalize_province, infer_category, infer_type

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.108.jobs"
SOURCE_ATTRIBUTION = "108.jobs"
REQUEST_DELAY = 2.5
ORIGIN_PROBE_TIMEOUT = 6

HEADERS = {
    "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    "Accept-Language": "lo, en;q=0.8",
}

# Careers page paths to probe on employer websites
CAREERS_PATHS = [
    "/careers", "/jobs", "/recruitment", "/vacancies",
    "/work-with-us", "/join-us", "/career",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, session: requests.Session, timeout: int = 15) -> BeautifulSoup | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        log.debug("Failed to fetch %s: %s", url, exc)
        return None


def _head_ok(url: str) -> bool:
    """Return True if a HEAD request returns 2xx."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=ORIGIN_PROBE_TIMEOUT, allow_redirects=True)
        return 200 <= r.status_code < 300
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Listing page helpers
# ---------------------------------------------------------------------------

def _get_job_urls(soup: BeautifulSoup) -> list[str]:
    urls = []
    for a in soup.select("a[href]"):
        href = a["href"]
        if "/job/" in href:
            full = href if href.startswith("http") else BASE_URL + href
            if full not in urls:
                urls.append(full)
    return urls


# ---------------------------------------------------------------------------
# Detail page parsers
# ---------------------------------------------------------------------------

def _extract_skills(soup: BeautifulSoup) -> list[str]:
    skills = []
    for el in soup.select(".skill, .tag, .badge, [class*=skill], [class*=tag]"):
        text = el.get_text(strip=True)
        if 2 <= len(text) <= 40:
            skills.append(text)
    return list(dict.fromkeys(skills))[:8]  # dedup, cap at 8


def _extract_company_url(soup: BeautifulSoup) -> str | None:
    for a in soup.select("[class*=company] a[href], [class*=employer] a[href], .company-website a"):
        href = a.get("href", "")
        if href.startswith("http") and "108.jobs" not in href:
            return href
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True).lower()
        if href.startswith("http") and "108.jobs" not in href and text in ("website", "company website", "visit"):
            return href
    return None


def _probe_careers_page(company_url: str) -> str | None:
    """Try known careers paths on the employer domain; return first reachable URL."""
    parsed = urlparse(company_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in CAREERS_PATHS:
        candidate = base + path
        if _head_ok(candidate):
            return candidate
    return None


def _extract_logo_url(soup: BeautifulSoup, source_url: str) -> str | None:
    for img in soup.select("[class*=company] img, [class*=employer] img, .logo img"):
        src = img.get("src") or img.get("data-src")
        if src:
            return urljoin(source_url, src)
    return None


# ---------------------------------------------------------------------------
# Main job parser
# ---------------------------------------------------------------------------

def _parse_job(soup: BeautifulSoup, url: str) -> dict | None:
    try:
        title_el = soup.select_one("h1.job-title, h1, .title")
        title = title_el.get_text(strip=True) if title_el else None

        company_el = soup.select_one(".company-name, .employer, [class*=company]")
        company = company_el.get_text(strip=True) if company_el else None

        location_el = soup.select_one(".location, [class*=location], [class*=province]")
        location = location_el.get_text(strip=True) if location_el else "Laos"

        description_el = soup.select_one(
            ".job-description, .description, [class*=description], article"
        )
        description = (
            description_el.get_text(separator="\n", strip=True) if description_el else None
        )
        if description:
            description = description[:4000]

        if not title or not company or not description:
            log.debug("Skipping %s — missing title/company/description", url)
            return None

        # Salary
        salary_el = soup.select_one(".salary, [class*=salary]")
        salary_raw = salary_el.get_text(strip=True) if salary_el else ""
        salary_min, salary_max = parse_salary(salary_raw)

        # Province
        province = canonicalize_province(location)

        # Category — prefer title match, fall back to full text
        full_text = f"{title} {description}"
        category = infer_category(title) or infer_category(full_text)

        # Job type
        type_el = soup.select_one("[class*=type], [class*=employment]")
        type_raw = type_el.get_text(strip=True) if type_el else ""
        job_type = infer_type(type_raw) or infer_type(full_text) or "FULL_TIME"

        # Skills from tag/badge elements
        skills = _extract_skills(soup)

        # Company domain for employer auto-claim
        company_url = _extract_company_url(soup)
        company_domain = None
        if company_url:
            m = re.search(r"https?://(?:www\.)?([^/]+)", company_url)
            if m:
                company_domain = m.group(1)

        logo_url = _extract_logo_url(soup, url)

        # Origin resolution: upgrade to EMPLOYER_DIRECT when careers page found
        source_type = "BOARD"
        source_url = url
        if company_url:
            careers_url = _probe_careers_page(company_url)
            if careers_url:
                source_type = "EMPLOYER_DIRECT"
                source_url = careers_url
                log.info("    ↑ Upgraded to EMPLOYER_DIRECT: %s", careers_url)

        payload: dict = {
            "title": title,
            "companyName": company,
            "location": location,
            "description": description,
            "sourceUrl": source_url,
            "sourceAttribution": SOURCE_ATTRIBUTION,
            "sourceType": source_type,
        }

        if province:
            payload["province"] = province
        if category:
            payload["category"] = category
        if skills:
            payload["skills"] = skills
        if job_type != "FULL_TIME":
            payload["type"] = job_type
        if salary_min is not None:
            payload["salaryMin"] = salary_min
        if salary_max is not None:
            payload["salaryMax"] = salary_max
        if company_domain:
            payload["companyDomain"] = company_domain

        # Company block for shadow-profile enrichment (non-destructive)
        company_block: dict = {}
        if company_url:
            company_block["website"] = company_url
            company_block["assetSourceUrl"] = url
        if logo_url:
            company_block["logoUrl"] = logo_url
        if company_block:
            payload["company"] = company_block

        return payload

    except Exception as exc:
        log.error("Error parsing %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Scrape loop
# ---------------------------------------------------------------------------

def scrape(max_pages: int = 5, dry_run: bool = False) -> None:
    session = requests.Session()
    batch: list[dict] = []

    for page in range(1, max_pages + 1):
        listing_url = f"{BASE_URL}/jobs?page={page}"
        log.info("Listing page %d: %s", page, listing_url)
        soup = _get(listing_url, session)
        if soup is None:
            log.warning("Could not fetch page %d — stopping.", page)
            break

        job_urls = _get_job_urls(soup)
        if not job_urls:
            log.info("No jobs on page %d — end of listings.", page)
            break

        log.info("Found %d jobs on page %d", len(job_urls), page)

        for job_url in job_urls:
            time.sleep(REQUEST_DELAY)
            detail_soup = _get(job_url, session)
            if detail_soup is None:
                continue
            payload = _parse_job(detail_soup, job_url)
            if payload:
                batch.append(payload)

        if batch:
            post_batch(batch, dry_run=dry_run)
            batch.clear()

        time.sleep(REQUEST_DELAY)

    log.info("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="108.jobs scraper for Job365")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=5)
    args = parser.parse_args()
    scrape(max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
