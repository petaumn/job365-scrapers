#!/usr/bin/env python3
"""
108.jobs → Job365 sourcing pipeline.

Fetches public job listings from 108.jobs (public API, ToS-friendly aggregator),
normalises each to the Job365 /jobs/source schema, and POSTs them.

Run:
    python3 scraper_108jobs.py [--dry-run] [--limit N] [--page-start P]
"""

import os, sys, json, time, re, argparse, logging, subprocess
from datetime import datetime, timezone
import urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("108jobs-scraper")

SOURCE_API_BASE  = "https://db.108.jobs/client-api"
JOB365_BASE      = "https://job365.ai/api/internal"
SOURCE_ATTR      = "108.jobs"
SOURCE_URL_TMPL  = "https://108.jobs/job_detail/{job_id}"
PER_PAGE         = 20
RATE_LIMIT_S     = 0.5   # between 108.jobs calls
POST_RATE_LIMIT  = 0.3   # between Job365 POSTs

# Category mapping: 108.jobs job function → Job365 category
CATEGORY_MAP = {
    "information technology": "Technology",
    "it support": "Technology",
    "it consulting": "Technology",
    "programming": "Technology",
    "software development": "Technology",
    "engineering": "Engineering",
    "accounting": "Accounting & Finance",
    "finance": "Accounting & Finance",
    "banking": "Banking & Finance",
    "marketing": "Marketing",
    "sales": "Sales",
    "media": "Media & Communications",
    "advertising": "Media & Communications",
    "editorial": "Media & Communications",
    "journalism": "Media & Communications",
    "hr": "Human Resources",
    "human resource": "Human Resources",
    "admin": "Administration",
    "administration": "Administration",
    "management": "Management",
    "education": "Education",
    "healthcare": "Healthcare",
    "hospitality": "Hospitality & Tourism",
    "tourism": "Hospitality & Tourism",
    "logistics": "Logistics & Supply Chain",
    "supply chain": "Logistics & Supply Chain",
    "construction": "Construction",
    "architecture": "Architecture & Design",
    "design": "Architecture & Design",
    "legal": "Legal",
    "manufacturing": "Manufacturing",
    "agriculture": "Agriculture",
    "customer service": "Customer Service",
    "retail": "Retail",
}

TYPE_MAP = {
    "full time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "part time": "PART_TIME",
    "parttime": "PART_TIME",
    "contract": "CONTRACT",
    "temporary": "TEMPORARY",
    "internship": "INTERNSHIP",
    "freelance": "FREELANCE",
}

PROVINCE_MAP = {
    "vientiane capital": "Vientiane",
    "vientiane prefecture": "Vientiane",
    "vientiane": "Vientiane",
    "luang prabang": "Luang Prabang",
    "savannakhet": "Savannakhet",
    "champasak": "Champasak",
    "khammouane": "Khammouane",
    "bokeo": "Bokeo",
    "houaphanh": "Houaphanh",
    "luang namtha": "Luang Namtha",
    "oudomxay": "Oudomxay",
    "phongsaly": "Phongsaly",
    "saravane": "Saravane",
    "sekong": "Sekong",
    "xaisomboun": "Xaisomboun",
    "xayaboury": "Xayaboury",
    "xiengkhouang": "Xieng Khouang",
}


def post_json(url, body, token=None, timeout=15):
    cmd = ["curl", "-s", "-w", "\n__STATUS__%{http_code}", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-d", json.dumps(body)]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    raw = r.stdout
    if "__STATUS__" in raw:
        body_part, status_part = raw.rsplit("__STATUS__", 1)
        status = int(status_part.strip())
    else:
        body_part, status = raw, 0
    try:
        return json.loads(body_part.strip()), status
    except Exception:
        return {"error": body_part.strip()[:200]}, status


def fetch_job_list(page=1, per_page=PER_PAGE):
    url = f"{SOURCE_API_BASE}/get-job-search-web?lang=en"
    body = {
        "page": page, "perPage": per_page,
        "title": "", "jobFunctionIds": [], "industryIds": [],
        "workingLocationIds": [], "jobExperienceId": [], "jobLanguageId": [],
        "jobEducationLevelId": [], "jobLevelId": [], "disabledPeople": "", "token": ""
    }
    result, status = post_json(url, body)
    return result


def fetch_job_detail(job_id):
    url = f"{SOURCE_API_BASE}/get-job-detail-web"
    result, _ = post_json(url, {"jobId": job_id, "token": ""})
    return result.get("jobDetail", {})


def strip_html(text):
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def map_category(job_functions):
    combined = " ".join(job_functions).lower()
    for key, cat in CATEGORY_MAP.items():
        if key in combined:
            return cat
    return "Other"


def map_province(location_str: str) -> str:
    loc_lower = location_str.lower()
    for key, prov in PROVINCE_MAP.items():
        if key in loc_lower:
            return prov
    return None


def build_description(detail, title, company, location):
    """Assemble a comprehensive description from all available 108.jobs detail fields."""
    parts = []

    desc = strip_html(detail.get("description", ""))
    if len(desc) >= 50:
        parts.append(desc)

    req = strip_html(detail.get("requirement", "") or detail.get("requirements", ""))
    if len(req) >= 20:
        parts.append("Requirements: " + req)

    benefit = strip_html(detail.get("benefit", "") or detail.get("benefits", ""))
    if len(benefit) >= 20:
        parts.append("Benefits: " + benefit)

    qual = strip_html(detail.get("qualification", "") or detail.get("qualifications", ""))
    if len(qual) >= 20:
        parts.append("Qualifications: " + qual)

    responsibility = strip_html(detail.get("responsibility", "") or detail.get("responsibilities", ""))
    if len(responsibility) >= 20:
        parts.append("Responsibilities: " + responsibility)

    combined = "\n\n".join(parts).strip()

    if len(combined) < 80:
        # Build a structured fallback using any available metadata
        edu_raw = ""
        edu_list = detail.get("jobEducationLevelId", [])
        if isinstance(edu_list, list) and edu_list:
            edu_raw = edu_list[0].get("name", "") if isinstance(edu_list[0], dict) else str(edu_list[0])
        exp_raw = ""
        exp_list = detail.get("jobExperienceId", [])
        if isinstance(exp_list, list) and exp_list:
            exp_raw = exp_list[0].get("name", "") if isinstance(exp_list[0], dict) else str(exp_list[0])
        level_raw = ""
        level_list = detail.get("jobLevelId", [])
        if isinstance(level_list, list) and level_list:
            level_raw = level_list[0].get("name", "") if isinstance(level_list[0], dict) else str(level_list[0])

        fallback_parts = [f"{title} at {company}."]
        if location:
            fallback_parts.append(f"Location: {location}.")
        if level_raw:
            fallback_parts.append(f"Level: {level_raw}.")
        if edu_raw:
            fallback_parts.append(f"Education: {edu_raw}.")
        if exp_raw:
            fallback_parts.append(f"Experience: {exp_raw}.")
        # Append any short description we did have
        if combined:
            fallback_parts.append(combined)
        combined = " ".join(fallback_parts)

    return combined[:5000]


def map_job_type(detail):
    """Derive job type from 108.jobs detail fields."""
    type_list = detail.get("jobTypeId", [])
    if isinstance(type_list, list) and type_list:
        raw = type_list[0].get("name", "").lower() if isinstance(type_list[0], dict) else str(type_list[0]).lower()
        for key, val in TYPE_MAP.items():
            if key in raw:
                return val
    employment = (detail.get("employmentType", "") or "").lower()
    for key, val in TYPE_MAP.items():
        if key in employment:
            return val
    return "FULL_TIME"


def normalize_job(detail):
    title = detail.get("title", "").strip()
    company = detail.get("companyName", "").strip()
    location = detail.get("workingLocations", "Laos").strip()
    job_id = detail.get("_id", "")

    if not title or not company or not job_id:
        return None

    description = build_description(detail, title, company, location)

    job_functions = [jf.get("name", "") for jf in detail.get("jobFunctionId", [])]
    category = map_category(job_functions)
    province = map_province(location)

    website = detail.get("website", "") or ""
    domain = None
    if website:
        m = re.search(r"https?://(?:www\.)?([^/]+)", website)
        if m:
            domain = m.group(1)

    skills = [jf for jf in job_functions if jf][:5]

    salary_min = detail.get("minSalary")
    salary_max = detail.get("maxSalary")
    job_type = map_job_type(detail)

    return {
        "title": title,
        "companyName": company,
        **({"companyDomain": domain} if domain else {}),
        "location": location,
        **({"province": province} if province else {}),
        "description": description,
        "skills": skills,
        "category": category,
        **({"salaryMin": int(salary_min)} if salary_min else {}),
        **({"salaryMax": int(salary_max)} if salary_max else {}),
        "type": job_type,
        "sourceUrl": SOURCE_URL_TMPL.format(job_id=job_id),
        "sourceAttribution": SOURCE_ATTR,
    }


def run(dry_run=False, limit=None, page_start=1):
    token = os.environ.get("JOB365_SOURCING_TOKEN")
    if not token:
        log.error("JOB365_SOURCING_TOKEN not set")
        sys.exit(1)

    log.info("Fetching job list page 1...")
    first_page = fetch_job_list(page=1)
    total = first_page.get("totals", 0)
    log.info(f"Total jobs on 108.jobs: {total}")

    all_jobs = first_page.get("allJob", [])
    page = page_start
    if page_start > 1:
        all_jobs = []

    pages_needed = (min(total, limit or total) + PER_PAGE - 1) // PER_PAGE

    while page <= pages_needed:
        if page > 1:
            log.info(f"Fetching page {page}/{pages_needed}...")
            result = fetch_job_list(page=page)
            all_jobs.extend(result.get("allJob", []))
            time.sleep(RATE_LIMIT_S)
        page += 1

    if limit:
        all_jobs = all_jobs[:limit]

    log.info(f"Processing {len(all_jobs)} jobs...")

    stats = {"submitted": 0, "duplicate": 0, "error": 0, "skipped": 0}
    results_log = []

    # Filter to actual job postings only
    all_jobs = [j for j in all_jobs if j.get("type") == "job"]
    log.info(f"After type filter: {len(all_jobs)} job postings")

    for i, job_summary in enumerate(all_jobs):
        job_id = job_summary.get("_id")
        if not job_id:
            stats["skipped"] += 1
            continue

        log.info(f"[{i+1}/{len(all_jobs)}] Fetching detail: {job_id} — {job_summary.get('title','?')}")
        detail = fetch_job_detail(job_id)
        time.sleep(RATE_LIMIT_S)

        payload = normalize_job(detail)
        if not payload:
            log.warning(f"  Skipped — could not normalize")
            stats["skipped"] += 1
            continue

        log.info(f"  → {payload['title']} @ {payload['companyName']} [{payload['category']}]")

        if dry_run:
            log.info(f"  DRY RUN — would POST: {json.dumps(payload)[:120]}...")
            stats["submitted"] += 1
            continue

        resp, status = post_json(
            f"{JOB365_BASE}/jobs/source",
            payload,
            token=token
        )
        time.sleep(POST_RATE_LIMIT)

        if status == 201:
            log.info(f"  ✓ Created: {resp.get('id', '?')} / {resp.get('slug', '?')}")
            stats["submitted"] += 1
            results_log.append({"id": resp.get("id"), "slug": resp.get("slug"), "title": payload["title"]})
        elif status == 409:
            log.info(f"  ~ Duplicate (409) — skipping")
            stats["duplicate"] += 1
        else:
            log.warning(f"  ✗ Error {status}: {resp}")
            stats["error"] += 1

    log.info(f"\n=== DONE ===")
    log.info(f"Submitted: {stats['submitted']} | Duplicates: {stats['duplicate']} | Errors: {stats['error']} | Skipped: {stats['skipped']}")

    # Write results log alongside the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, f"run_log_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_path, "w") as f:
        json.dump({"stats": stats, "jobs": results_log, "source": SOURCE_ATTR}, f, indent=2)
    log.info(f"Log written: {log_path}")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't actually POST to Job365")
    parser.add_argument("--limit", type=int, default=None, help="Max jobs to process")
    parser.add_argument("--page-start", type=int, default=1, help="Start from page N")
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit, page_start=args.page_start)
