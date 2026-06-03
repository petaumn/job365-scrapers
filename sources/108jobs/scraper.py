"""
Scraper for 108.jobs — Lao job board.

Run:
    export JOB365_SOURCING_TOKEN=...
    python sources/108jobs/scraper.py [--dry-run] [--max-pages 3]

Output: posts scraped jobs to Job365 API via scripts/post.py
"""
import sys
import time
import logging
import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Allow running from repo root or sources/108jobs/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.post import post_batch

BASE_URL = "https://www.108.jobs"
SOURCE_ATTRIBUTION = "108.jobs"
REQUEST_DELAY = 2.5  # seconds between page fetches — be polite

HEADERS = {
    "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    "Accept-Language": "lo, en;q=0.8",
}

# Province normalisation: 108.jobs city strings → standard province names
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

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _get(url: str, session: requests.Session) -> BeautifulSoup | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        log.warning("Fetch failed for %s: %s", url, e)
        return None


def _extract_job_urls(soup: BeautifulSoup) -> list[str]:
    """Extract individual job listing URLs from a search/listing page."""
    urls = []
    for a in soup.select("a[href]"):
        href = a["href"]
        # 108.jobs job detail pages follow /job/<slug> pattern
        if "/job/" in href and href not in urls:
            full = href if href.startswith("http") else BASE_URL + href
            urls.append(full)
    return urls


def _normalise_province(raw_location: str) -> tuple[str, str | None]:
    """Return (location, province) from a raw location string."""
    location = raw_location.strip()
    for key, province in PROVINCE_MAP.items():
        if key in location:
            return location, province
    return location, None


def _parse_job(soup: BeautifulSoup, url: str) -> dict | None:
    """Parse a single job detail page into a Job365 payload."""
    try:
        title_el = soup.select_one("h1") or soup.select_one(".job-title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        company_el = soup.select_one(".company-name") or soup.select_one("[class*='employer']")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        location_el = soup.select_one(".location") or soup.select_one("[class*='location']")
        raw_location = location_el.get_text(strip=True) if location_el else "Laos"
        location, province = _normalise_province(raw_location)

        # Description: prefer full .description block; fall back to meta description
        desc_el = soup.select_one(".description") or soup.select_one("[class*='description']")
        if desc_el:
            description = desc_el.get_text(" ", strip=True)
        else:
            meta = soup.find("meta", attrs={"name": "description"})
            description = meta["content"].strip() if meta and meta.get("content") else ""

        if len(description) < 20:
            description = f"{title} at {company} in {location}. See {url} for full details."

        payload: dict = {
            "title": title,
            "companyName": company,
            "location": location,
            "description": description[:4000],  # API limit guard
            "sourceUrl": url,
            "sourceAttribution": SOURCE_ATTRIBUTION,
        }

        if province:
            payload["province"] = province

        return payload

    except Exception as e:
        log.warning("Parse error for %s: %s", url, e)
        return None


def scrape(max_pages: int = 5, dry_run: bool = False) -> list[dict]:
    """Scrape up to max_pages pages of listings from 108.jobs."""
    session = requests.Session()
    all_payloads: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        page_url = f"{BASE_URL}/jobs?page={page}"
        log.info("Fetching listing page %d: %s", page, page_url)
        soup = _get(page_url, session)
        if not soup:
            break

        job_urls = _extract_job_urls(soup)
        job_urls = [u for u in job_urls if u not in seen_urls]

        if not job_urls:
            log.info("No new listings on page %d — stopping pagination", page)
            break

        log.info("Found %d job URLs on page %d", len(job_urls), page)

        for job_url in job_urls:
            seen_urls.add(job_url)
            time.sleep(REQUEST_DELAY)
            detail = _get(job_url, session)
            if not detail:
                continue
            payload = _parse_job(detail, job_url)
            if payload:
                all_payloads.append(payload)

        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    log.info("Scraped %d payloads total", len(all_payloads))

    if all_payloads:
        results = post_batch(all_payloads, delay_seconds=1.0, dry_run=dry_run)
        posted = sum(1 for r in results if r.get("status") == 201)
        skipped = sum(1 for r in results if r.get("status") == 409)
        log.info("Done — posted=%d skipped(dup)=%d", posted, skipped)

    return all_payloads


def main():
    parser = argparse.ArgumentParser(description="108.jobs scraper for Job365.ai")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not POST to API")
    parser.add_argument("--max-pages", type=int, default=5, help="Max listing pages to fetch")
    args = parser.parse_args()

    if args.dry_run:
        log.info("DRY-RUN mode — no API calls will be made")

    scrape(max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
