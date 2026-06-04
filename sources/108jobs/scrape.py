"""
sources/108jobs/scrape.py — Scraper for 108.jobs (Lao job board).

PR #3 features:
  - sourceType: BOARD by default; upgrades to EMPLOYER_DIRECT when employer
    careers page is found and reachable.
  - company block: logo, about, website, socials, assetSourceUrl sent when available.
  - category: mapped to the 10 canonical Job365 categories; omitted when ambiguous.
  - skills: extracted from page tags/keywords section.
  - type: FULL_TIME / PART_TIME / CONTRACT / INTERNSHIP / FREELANCE.
  - salaryMin / salaryMax in LAK/month when shown.
  - province: canonical slug (e.g. "vientiane-capital", "savannakhet").
  - companyDomain: extracted from company website URL.

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
from lib.post import post_batch, parse_salary

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.108.jobs"
SOURCE_ATTRIBUTION = "108.jobs"
REQUEST_DELAY = 2.5
ORIGIN_PROBE_TIMEOUT = 6  # kept short so we don't stall the pipeline

HEADERS = {
    "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    "Accept-Language": "lo, en;q=0.8",
}

# ---------------------------------------------------------------------------
# Province display name / Lao script → canonical slug
# Slugs match src/lib/data/provinces.ts on the Job365 platform.
# ---------------------------------------------------------------------------

PROVINCE_MAP: dict[str, str] = {
    # Vientiane Capital
    "ນະຄອນຫຼວວຽງຈັນ": "vientiane-capital",
    "vientiane capital": "vientiane-capital",
    "vientiane prefecture": "vientiane-capital",
    "nakhon luang vientiane": "vientiane-capital",
    # plain "vientiane" → capital (most 108.jobs listings mean the capital)
    "vientiane": "vientiane-capital",
    "ວຽງຈັນ": "vientiane-capital",
    # Vientiane Province (only when "province" qualifier is present)
    "ແຂວງວຽງຈັນ": "vientiane",
    "vientiane province": "vientiane",
    # Savannakhet
    "ສະຫວັນນະເຂດ": "savannakhet",
    "savannakhet": "savannakhet",
    # Luang Prabang
    "ຫຼວງພະບາງ": "luang-prabang",
    "luang prabang": "luang-prabang",
    # Champasak / Pakse
    "ຈຳປາສັກ": "champasak",
    "champasak": "champasak",
    "ປາກເສ": "champasak",
    "pakse": "champasak",
    # Khammouane
    "ຄຳມ່ວນ": "khammouane",
    "khammouane": "khammouane",
    # Bolikhamsai
    "ບອລິຄຳໄສ": "bolikhamsai",
    "bolikhamsai": "bolikhamsai",
    "bolikhamxai": "bolikhamsai",
    # Houaphanh
    "ຫວຣພັນ": "houaphanh",
    "houaphanh": "houaphanh",
    # Oudomxay
    "ອຸດົມໄສ": "oudomxay",
    "oudomxay": "oudomxay",
    # Bokeo
    "ບອ່ແກ້ວ": "bokeo",
    "bokeo": "bokeo",
    # Xieng Khouang
    "ຊຽງຂວາງ": "xieng-khouang",
    "xieng khouang": "xieng-khouang",
    "xiengkhouang": "xieng-khouang",
    # Phongsaly
    "ຜົ້ງສາລີ": "phongsaly",
    "phongsaly": "phongsaly",
    # Attapeu
    "ອັດຕະປື": "attapeu",
    "attapeu": "attapeu",
    # Sekong
    "ເຊກອງ": "sekong",
    "sekong": "sekong",
    # Xaisomboun
    "ໄສສົມບູນ": "xaisomboun",
    "xaisomboun": "xaisomboun",
    # Salavan
    "ສາລະວັນ": "salavan",
    "saravane": "salavan",
    "salavan": "salavan",
    # Xayaboury
    "ໄສຍະບູລີ": "xayaboury",
    "xayaboury": "xayaboury",
    # Luang Namtha
    "ຫຼວງນ້ຳທາ": "luang-namtha",
    "luang namtha": "luang-namtha",
}

# ---------------------------------------------------------------------------
# Keyword → canonical Job365 category (10 values only; ordered list, first hit wins)
# Omit category entirely when ambiguous — server infers from title/description.
# ---------------------------------------------------------------------------

CATEGORY_MAP: list[tuple[str, str]] = [
    # Engineering & IT — specific tech terms checked before broad "engineering"
    ("software", "Engineering & IT"),
    ("developer", "Engineering & IT"),
    ("programmer", "Engineering & IT"),
    ("information technology", "Engineering & IT"),
    ("it support", "Engineering & IT"),
    ("network engineer", "Engineering & IT"),
    ("cyber", "Engineering & IT"),
    ("data analyst", "Engineering & IT"),
    ("data scientist", "Engineering & IT"),
    ("system admin", "Engineering & IT"),
    ("web developer", "Engineering & IT"),
    ("mobile developer", "Engineering & IT"),
    # Banking & Finance
    ("banking", "Banking & Finance"),
    ("bank ", "Banking & Finance"),
    ("finance manager", "Banking & Finance"),
    ("accountant", "Banking & Finance"),
    ("accounting", "Banking & Finance"),
    ("audit", "Banking & Finance"),
    ("insurance", "Banking & Finance"),
    ("loan officer", "Banking & Finance"),
    ("credit analyst", "Banking & Finance"),
    ("treasurer", "Banking & Finance"),
    # Sales & Marketing
    ("sales", "Sales & Marketing"),
    ("marketing", "Sales & Marketing"),
    ("brand", "Sales & Marketing"),
    ("business development", "Sales & Marketing"),
    ("digital marketing", "Sales & Marketing"),
    ("social media", "Sales & Marketing"),
    ("communications", "Sales & Marketing"),
    ("customer success", "Sales & Marketing"),
    # NGO & Development
    ("ngo", "NGO & Development"),
    ("ingo", "NGO & Development"),
    ("development officer", "NGO & Development"),
    ("programme officer", "NGO & Development"),
    ("project coordinator", "NGO & Development"),
    ("humanitarian", "NGO & Development"),
    ("united nations", "NGO & Development"),
    # Education & Training
    ("teacher", "Education & Training"),
    ("education", "Education & Training"),
    ("training officer", "Education & Training"),
    ("lecturer", "Education & Training"),
    ("tutor", "Education & Training"),
    # Healthcare
    ("doctor", "Healthcare"),
    ("nurse", "Healthcare"),
    ("healthcare", "Healthcare"),
    ("medical", "Healthcare"),
    ("pharmacist", "Healthcare"),
    ("clinic", "Healthcare"),
    ("hospital", "Healthcare"),
    # Hospitality & Tourism
    ("hotel", "Hospitality & Tourism"),
    ("hospitality", "Hospitality & Tourism"),
    ("tourism", "Hospitality & Tourism"),
    ("restaurant", "Hospitality & Tourism"),
    ("chef", "Hospitality & Tourism"),
    ("front desk", "Hospitality & Tourism"),
    ("barista", "Hospitality & Tourism"),
    # Logistics & Supply Chain
    ("logistics", "Logistics & Supply Chain"),
    ("supply chain", "Logistics & Supply Chain"),
    ("warehouse", "Logistics & Supply Chain"),
    ("procurement", "Logistics & Supply Chain"),
    ("driver", "Logistics & Supply Chain"),
    ("delivery", "Logistics & Supply Chain"),
    ("import", "Logistics & Supply Chain"),
    ("export", "Logistics & Supply Chain"),
    # Manufacturing — civil/mechanical/electrical engineer before generic "engineering"
    ("civil engineer", "Manufacturing"),
    ("electrical engineer", "Manufacturing"),
    ("mechanical engineer", "Manufacturing"),
    ("manufacturing", "Manufacturing"),
    ("production", "Manufacturing"),
    ("construction", "Manufacturing"),
    ("factory", "Manufacturing"),
    ("quality control", "Manufacturing"),
    # Admin & HR — broad terms placed last to avoid false positives
    ("human resource", "Admin & HR"),
    ("hr manager", "Admin & HR"),
    ("recruitment", "Admin & HR"),
    ("administration", "Admin & HR"),
    ("secretary", "Admin & HR"),
    ("receptionist", "Admin & HR"),
    ("office manager", "Admin & HR"),
    ("legal", "Admin & HR"),
    ("compliance", "Admin & HR"),
    ("operations manager", "Admin & HR"),
    ("customer service", "Admin & HR"),
]

TYPE_MAP: dict[str, str] = {
    "full time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "full-time": "FULL_TIME",
    "part time": "PART_TIME",
    "parttime": "PART_TIME",
    "part-time": "PART_TIME",
    "contract": "CONTRACT",
    "temporary": "TEMPORARY",
    "internship": "INTERNSHIP",
    "intern": "INTERNSHIP",
    "freelance": "FREELANCE",
}

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
    """Return True if a HEAD request to url returns 2xx."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=ORIGIN_PROBE_TIMEOUT,
                          allow_redirects=True)
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

def _normalise_province(raw: str) -> str | None:
    """Return canonical province slug, or None when unrecognisable."""
    low = raw.lower().strip()
    if low in PROVINCE_MAP:
        return PROVINCE_MAP[low]
    # Substring match — longest key wins
    best_len, best_slug = 0, None
    for key, slug in PROVINCE_MAP.items():
        if key in low and len(key) > best_len:
            best_len, best_slug = len(key), slug
    return best_slug


def _infer_category(text: str) -> str | None:
    """First-match on ordered CATEGORY_MAP; returns None when ambiguous."""
    low = text.lower()
    for keyword, cat in CATEGORY_MAP:
        if keyword in low:
            return cat
    return None


def _infer_type(text: str) -> str | None:
    low = text.lower()
    for keyword, jtype in TYPE_MAP.items():
        if keyword in low:
            return jtype
    return None


def _extract_skills(soup: BeautifulSoup) -> list[str]:
    skills = []
    for el in soup.select(".skill, .tag, .badge, [class*=skill], [class*=tag]"):
        text = el.get_text(strip=True)
        if 2 <= len(text) <= 40:
            skills.append(text)
    return list(dict.fromkeys(skills))[:8]


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
    """Return the first reachable careers URL on the employer's domain, or None."""
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


def _extract_company_about(soup: BeautifulSoup) -> str | None:
    """Extract company description from the employer section of the listing."""
    for el in soup.select(
        "[class*=company-about], [class*=company-desc], "
        "[class*=about-company], [class*=employer-desc], [class*=company-info]"
    ):
        text = el.get_text(separator=" ", strip=True)
        if len(text) >= 40:
            return text[:500]
    return None


def _extract_social_links(soup: BeautifulSoup) -> dict[str, str]:
    """Extract Facebook and LinkedIn page links. Skips auth-walled profile URLs."""
    socials: dict[str, str] = {}
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "facebook.com" in href and "facebookUrl" not in socials:
            # Only public page URLs (not auth-required /login redirects)
            if "/login" not in href and "/l.php" not in href:
                socials["facebookUrl"] = href
        elif "linkedin.com/company" in href and "linkedinUrl" not in socials:
            socials["linkedinUrl"] = href
    return socials


# ---------------------------------------------------------------------------
# Factual summary for BOARD fallback
# ---------------------------------------------------------------------------

def _build_factual_summary(
    title: str,
    company: str,
    location: str,
    description_raw: str,
    skills: list[str],
    salary_min: int | None,
    salary_max: int | None,
    job_type: str,
) -> str:
    """
    Compose a factual description from structured listing data.
    Goal: >= 120 chars, no verbatim copy of the board's expressive prose.
    Falls back to truncated raw text when structured data is insufficient.
    """
    parts: list[str] = []

    parts.append(f"{company} is hiring a {title} based in {location}.")

    if job_type and job_type != "FULL_TIME":
        label = job_type.replace("_", " ").title()
        parts.append(f"This is a {label} position.")

    if salary_min and salary_max:
        parts.append(f"Salary: {salary_min:,}–{salary_max:,} LAK/month.")
    elif salary_min:
        parts.append(f"Salary from {salary_min:,} LAK/month.")

    if skills:
        parts.append(f"Key skills: {', '.join(skills[:5])}.")

    # Pull short fact-lines from raw description (responsibilities / requirements)
    if description_raw:
        lines = [ln.strip() for ln in description_raw.splitlines() if ln.strip()]
        fact_lines = [ln for ln in lines if 10 <= len(ln) <= 120][:3]
        if fact_lines:
            parts.extend(fact_lines)

    summary = " ".join(parts)

    # Fallback: if structured data alone is too thin, use truncated raw text
    if len(summary) < 120 and description_raw:
        summary = description_raw[:600].strip()

    return summary


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
        location = location_el.get_text(strip=True) if location_el else "Vientiane"

        description_el = soup.select_one(
            ".job-description, .description, [class*=description], article"
        )
        description_raw = (
            description_el.get_text(separator="\n", strip=True) if description_el else ""
        )

        if not title or not company:
            log.debug("Skipping %s — missing title/company", url)
            return None

        # Salary
        salary_el = soup.select_one(".salary, [class*=salary]")
        salary_raw = salary_el.get_text(strip=True) if salary_el else ""
        salary_min, salary_max = parse_salary(salary_raw)

        # Province slug
        province = _normalise_province(location)

        # Category: title first (more signal-dense), then full text
        category = _infer_category(title) or _infer_category(description_raw)

        # Job type
        type_el = soup.select_one("[class*=type], [class*=employment]")
        type_raw = type_el.get_text(strip=True) if type_el else ""
        job_type = _infer_type(type_raw) or _infer_type(description_raw) or "FULL_TIME"

        # Skills
        skills = _extract_skills(soup)

        # Company URL and domain
        company_url = _extract_company_url(soup)
        company_domain: str | None = None
        if company_url:
            m = re.search(r"https?://(?:www\.)?([^/]+)", company_url)
            if m:
                company_domain = m.group(1)

        logo_url = _extract_logo_url(soup, url)
        company_about = _extract_company_about(soup)
        social_links = _extract_social_links(soup)

        # Origin resolution
        source_type = "BOARD"
        source_url = url
        if company_url:
            careers_url = _probe_careers_page(company_url)
            if careers_url:
                source_type = "EMPLOYER_DIRECT"
                source_url = careers_url
                log.info("    ↑ EMPLOYER_DIRECT: %s", careers_url)

        # Factual description (no verbatim board copy)
        description = _build_factual_summary(
            title, company, location, description_raw,
            skills, salary_min, salary_max, job_type,
        )
        if not description:
            log.debug("Skipping %s — empty description", url)
            return None

        payload: dict = {
            "title": title,
            "companyName": company,
            "location": location,
            "description": description,
            "sourceUrl": source_url,
            "sourceAttribution": SOURCE_ATTRIBUTION,
            "sourceType": source_type,
            "type": job_type,
        }

        if province:
            payload["province"] = province
        if category:
            payload["category"] = category
        if skills:
            payload["skills"] = skills
        if salary_min is not None:
            payload["salaryMin"] = salary_min
        if salary_max is not None:
            payload["salaryMax"] = salary_max
        if company_domain:
            payload["companyDomain"] = company_domain

        # Company block — feeds shadow profile (non-destructive; unclaimed orgs only)
        company_block: dict = {}
        if company_url:
            company_block["website"] = company_url
            company_block["assetSourceUrl"] = url  # 108.jobs page is the asset origin
        if logo_url:
            company_block["logoUrl"] = logo_url
        if company_about:
            company_block["about"] = company_about
        company_block.update(social_links)
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
    stats = {"total": 0, "upgraded": 0, "with_salary": 0, "with_skills": 0}

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
                stats["total"] += 1
                if payload.get("sourceType") == "EMPLOYER_DIRECT":
                    stats["upgraded"] += 1
                if payload.get("salaryMin"):
                    stats["with_salary"] += 1
                if payload.get("skills"):
                    stats["with_skills"] += 1
                batch.append(payload)

        if batch:
            post_batch(batch, dry_run=dry_run)
            batch.clear()

        time.sleep(REQUEST_DELAY)

    total = max(stats["total"], 1)
    log.info(
        "Done — total=%d  employer_direct=%d (%.0f%%)  salary=%d (%.0f%%)  skills=%d (%.0f%%)",
        stats["total"],
        stats["upgraded"], 100 * stats["upgraded"] / total,
        stats["with_salary"], 100 * stats["with_salary"] / total,
        stats["with_skills"], 100 * stats["with_skills"] / total,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="108.jobs scraper for Job365")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=5)
    args = parser.parse_args()
    scrape(max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
