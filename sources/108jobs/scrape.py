"""
sources/108jobs/scrape.py — Scraper for 108.jobs (Lao job board).

Run:
    export JOB365_SOURCING_TOKEN=...
    python -m sources.108jobs.scrape [--dry-run] [--max-pages 3]

Output: posts scraped jobs to Job365 API via lib.post.post_batch
"""
import sys
import time
import logging
import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Allow running as a module from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.post import post_batch, parse_salary

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.108.jobs"
SOURCE_ATTRIBUTION = "108.jobs"
REQUEST_DELAY = 2.5

HEADERS = {
    "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    "Accept-Language": "lo, en;q=0.8",
}

PROVINCE_MAP = {
    "ວຽງຈັນ": "Vientiane Prefecture",
    "Vientiane": "Vientiane Prefecture",
    "ສາວັນນະເຂດ": "Savannakhet",
    "Savannakhet": "Savannakhet",
    "ຫຼວງພະບາງ": "Luang Prabang",
    "Luang Prabang": "Luang Prabang",
    "ຈຳປາສັກ": "Champasak",
    "Champasak": "Champasak",
    "ປາກເຊ": "Champasak",
    "Pakse": "Champasak",
    "ບໍລິຄຳໄຊ": "Bolikhamxai",
    "ຄຳມ່ວນ": "Khammouane",
    "ຫົວພັນ": "Huaphanh",
    "ອຸດົມໄຊ": "Oudomxai",
    "ໜອງຄາຍ": "Vientiane Province",
}


def _get(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on error."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
        return None


def _extract_job_urls(soup: BeautifulSoup) -> list[str]:
    """Return all /job/<slug> absolute URLs found on a listing page."""
    urls = []
    for a in soup.select("a[href]"):
        href = a["href"]
        if "/job/" in href:
            full = href if href.startswith("http") else BASE_URL + href
            if full not in urls:
                urls.append(full)
    return urls


def _normalise_province(raw_location: str) -> str | None:
    """Map a raw location string to a canonical province name."""
    for key, province in PROVINCE_MAP.items():
        if key.lower() in raw_location.lower():
            return province
    return None


def _parse_job(soup: BeautifulSoup, url: str) -> dict | None:
    """
    Parse a 108.jobs detail page into a Job365 API payload dict.

    Returns None if required fields cannot be extracted.
    """
    try:
        title_el = soup.select_one("h1.job-title, h1, .title")
        title = title_el.get_text(strip=True) if title_el else None

        company_el = soup.select_one(".company-name, .employer, [class*=company]")
        company = company_el.get_text(strip=True) if company_el else None

        location_el = soup.select_one(".location, [class*=location], [class*=province]")
        location = location_el.get_text(strip=True) if location_el else "Vientiane"

        description_el = soup.select_one(".job-description, .description, [class*=description], article")
        description = description_el.get_text(separator="\n", strip=True) if description_el else None
        if description:
            description = description[:4000]

        if not title or not company or not description:
            log.debug("Skipping %s — missing title/company/description", url)
            return None

        salary_el = soup.select_one(".salary, [class*=salary]")
        salary_raw = salary_el.get_text(strip=True) if salary_el else ""
        salary_min, salary_max = parse_salary(salary_raw)

        province = _normalise_province(location)

        payload: dict = {
            "title": title,
            "companyName": company,
            "location": location,
            "description": description,
            "sourceUrl": url,
            "sourceAttribution": SOURCE_ATTRIBUTION,
        }
        if province:
            payload["province"] = province
        if salary_min is not None:
            payload["salaryMin"] = salary_min
        if salary_max is not None:
            payload["salaryMax"] = salary_max

        return payload

    except Exception as exc:
        log.error("Error parsing %s: %s", url, exc)
        return None


def scrape(max_pages: int = 5, dry_run: bool = False) -> None:
    """Main scraping loop: paginate listing, parse each detail page, post batch."""
    session = requests.Session()
    batch: list[dict] = []

    for page in range(1, max_pages + 1):
        listing_url = f"{BASE_URL}/jobs?page={page}"
        log.info("Fetching listing page %d: %s", page, listing_url)
        soup = _get(listing_url, session)
        if soup is None:
            log.warning("Could not fetch page %d — stopping.", page)
            break

        job_urls = _extract_job_urls(soup)
        if not job_urls:
            log.info("No job URLs found on page %d — end of listings.", page)
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

    log.info("Scrape complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="108.jobs scraper for Job365")
    parser.add_argument("--dry-run", action="store_true", help="Print jobs without posting")
    parser.add_argument("--max-pages", type=int, default=5, help="Max listing pages to scrape")
    args = parser.parse_args()

    scrape(max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
