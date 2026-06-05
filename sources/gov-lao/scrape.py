"""
sources/gov-lao/scrape.py — Scraper for Lao government job portals.

Primary source: National Employment Service Centre (nesc.gov.la)
  — operated by the Ministry of Labour and Social Welfare (MLSW)
  — sourceType: GOV_PORTAL (platform priority 4, above BOARD=2)

Run:
    export JOB365_SOURCING_TOKEN=...
    python sources/gov-lao/scrape.py [--dry-run] [--max-pages 5]

Selector notes: NESC website selectors were identified from the site as of
June 2026. Update the CSS selectors in _get_job_urls/_parse_job if the
site is redesigned, then re-run with --dry-run to verify coverage.
"""
from __future__ import annotations

import re
import sys
import time
import logging
import argparse
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.post import post_batch, parse_salary
from lib.normalize import canonicalize_province, infer_category, infer_type

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://nesc.gov.la"
SOURCE_ATTRIBUTION = "nesc.gov.la"
SOURCE_TYPE = "GOV_PORTAL"
REQUEST_DELAY = 3.0

HEADERS = {
    "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    "Accept-Language": "lo, en;q=0.8",
}

# NESC listing entry points — first URL that returns job links wins
LISTING_PATHS = [
    "/jobs",
    "/vacancy",
    "/vacancies",
    "/job-listing",
    "/en/jobs",
    "/lo/jobs",
    "/recruitment",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, session: requests.Session, timeout: int = 20) -> BeautifulSoup | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        log.debug("Failed to fetch %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Listing page helpers
# ---------------------------------------------------------------------------

def _get_job_urls(soup: BeautifulSoup, page_url: str) -> list[str]:
    """Extract unique job-detail URLs from an NESC listing page."""
    urls: list[str] = []
    # Broad selector set to handle different NESC page versions.
    # Restrict to links that look like individual job/vacancy pages.
    for a in soup.select(
        "a[href*='/job/'], a[href*='/vacancy/'], a[href*='/position/'], "
        "a[href*='/jobs/'], a[href*='/vacancies/'], "
        ".job-item a, .vacancy-item a, .job-list a, "
        ".job-title a, .position-title a, "
        "h2 > a, h3 > a"
    ):
        href = a.get("href", "")
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        full = href if href.startswith("http") else urljoin(page_url, href)
        # Stay within nesc.gov.la and avoid listing/category pages
        if "nesc.gov.la" in full and full != page_url and full not in urls:
            urls.append(full)
    return urls


def _get_next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    """Return URL of the next pagination page, or None."""
    for a in soup.select(
        "a.next, a[rel='next'], .pagination a:last-child, "
        "li.next a, .pager-next a, a[aria-label='Next']"
    ):
        href = a.get("href", "")
        if href and href not in ("#", current_url):
            return href if href.startswith("http") else urljoin(current_url, href)
    return None


# ---------------------------------------------------------------------------
# Detail page parser
# ---------------------------------------------------------------------------

def _first_text(soup: BeautifulSoup, *selectors: str) -> str | None:
    """Try CSS selectors in order; return first non-empty text."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            if text:
                return text
    return None


def _extract_logo(soup: BeautifulSoup, page_url: str) -> str | None:
    for img in soup.select(
        ".org-logo img, .ministry-logo img, .employer-logo img, "
        ".logo img, .seal img, header img"
    ):
        src = img.get("src") or img.get("data-src") or ""
        if src and not src.endswith(("favicon.ico", "icon.png", "logo-white.png")):
            return urljoin(page_url, src)
    return None


def _parse_job(soup: BeautifulSoup, url: str) -> dict | None:
    try:
        title = _first_text(
            soup,
            "h1.job-title", "h1.position-title", "h1.vacancy-title",
            ".job-title", ".position-title", ".vacancy-title",
            "h1", "h2.entry-title",
        )

        # Organisation (ministry / department). Government jobs on NESC
        # always have a posting agency; default to the portal name only as
        # last resort.
        company = _first_text(
            soup,
            ".organization-name", ".organisation-name",
            ".ministry-name", ".department-name",
            ".employer-name", ".company-name",
            "[class*=organisation]", "[class*=organization]",
            "[class*=ministry]", "[class*=department]",
        ) or "Government of Laos"

        location = _first_text(
            soup,
            ".location", "[class*=location]", "[class*=province]",
            ".job-location", ".place", ".region",
        ) or "Laos"

        desc_el = soup.select_one(
            ".job-description, .job-detail, .description, "
            "[class*=description], [class*=job-content], "
            ".content-body, .entry-content, article, main"
        )
        description: str | None = None
        if desc_el:
            raw = desc_el.get_text(separator="\n", strip=True)
            description = raw[:4000] if raw else None

        if not title:
            log.debug("Skipping %s — no title", url)
            return None
        if not description or len(description) < 50:
            log.debug("Skipping %s — description too short (%d chars)",
                      url, len(description or ""))
            return None

        # Salary (rare on government postings — included when published)
        salary_raw = _first_text(
            soup, ".salary", "[class*=salary]", "[class*=compensation]"
        ) or ""
        salary_min, salary_max = parse_salary(salary_raw)

        province = canonicalize_province(location)

        # Category inferred from title first, fall back to full text
        category = infer_category(title) or infer_category(f"{title} {description}")

        type_raw = _first_text(
            soup, "[class*=job-type]", "[class*=employment-type]",
            "[class*=contract-type]",
        ) or ""
        job_type = infer_type(type_raw) or infer_type(title) or "FULL_TIME"

        # Skills listed in dedicated skill/requirement blocks
        skills: list[str] = []
        for el in soup.select(
            ".skill, .tag, .badge, [class*=skill], [class*=required-skill]"
        ):
            text = el.get_text(strip=True)
            if 2 <= len(text) <= 40 and not text.endswith(":"):
                skills.append(text)
        skills = list(dict.fromkeys(skills))[:8]

        # Ministry/agency website link (for shadow profile enrichment)
        website: str | None = None
        company_domain: str | None = None
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            label = a.get_text(strip=True).lower()
            if (
                href.startswith("http")
                and "nesc.gov.la" not in href
                and ".gov.la" in href
                and label in ("website", "visit", "ເວັບໄຊ", "official site")
            ):
                website = href
                m = re.search(r"https?://(?:www\.)?([^/]+)", href)
                if m:
                    company_domain = m.group(1)
                break

        logo_url = _extract_logo(soup, url)

        payload: dict = {
            "title": title,
            "companyName": company,
            "location": location,
            "description": description,
            "sourceUrl": url,
            "sourceAttribution": SOURCE_ATTRIBUTION,
            "sourceType": SOURCE_TYPE,
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

        company_block: dict = {}
        if website:
            company_block["website"] = website
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

def _resolve_listing_url(session: requests.Session) -> str | None:
    """Try each listing path and return the first that serves job links."""
    for path in LISTING_PATHS:
        url = BASE_URL + path
        soup = _get(url, session)
        if soup and _get_job_urls(soup, url):
            log.info("Found active listing page: %s", url)
            return url
        time.sleep(1)
    return None


def scrape(max_pages: int = 10, dry_run: bool = False) -> None:
    session = requests.Session()
    batch: list[dict] = []
    stats = {"attempted": 0, "posted": 0, "skipped": 0}

    listing_url = _resolve_listing_url(session)
    if not listing_url:
        log.warning(
            "Could not find an active job listing page on %s. "
            "Update LISTING_PATHS if the site has been restructured.",
            BASE_URL,
        )
        return

    page_num = 0
    while listing_url and page_num < max_pages:
        page_num += 1
        log.info("Page %d: %s", page_num, listing_url)

        soup = _get(listing_url, session)
        if soup is None:
            log.warning("Could not fetch page %d — stopping.", page_num)
            break

        job_urls = _get_job_urls(soup, listing_url)
        if not job_urls:
            log.info("No jobs on page %d — end of listings.", page_num)
            break

        log.info("Found %d jobs on page %d", len(job_urls), page_num)

        for job_url in job_urls:
            stats["attempted"] += 1
            time.sleep(REQUEST_DELAY)
            detail_soup = _get(job_url, session)
            if detail_soup is None:
                stats["skipped"] += 1
                continue
            payload = _parse_job(detail_soup, job_url)
            if payload:
                batch.append(payload)
                stats["posted"] += 1
            else:
                stats["skipped"] += 1

        if batch:
            post_batch(batch, dry_run=dry_run)
            batch.clear()

        listing_url = _get_next_page_url(soup, listing_url)
        time.sleep(REQUEST_DELAY)

    log.info(
        "Done — attempted=%d posted=%d skipped=%d",
        stats["attempted"], stats["posted"], stats["skipped"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lao gov portals scraper for Job365 (primary: nesc.gov.la)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and log jobs without posting to API")
    parser.add_argument("--max-pages", type=int, default=10,
                        help="Maximum listing pages to fetch (default: 10)")
    args = parser.parse_args()
    scrape(max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
