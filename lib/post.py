"""
lib/post.py — shared helpers for Job365 sourcing API.

Provides:
  post_batch(jobs, dry_run)  — POST a list of job dicts to /api/internal/jobs/source
  parse_salary(raw)          — parse salary strings into (min_lak, max_lak) or (None, None)
"""
import os
import re
import logging
import requests

log = logging.getLogger(__name__)

JOB365_BASE_URL = os.environ.get("JOB365_BASE_URL", "https://job365.ai")
JOB365_SOURCING_TOKEN = os.environ.get("JOB365_SOURCING_TOKEN", "")

ENDPOINT = f"{JOB365_BASE_URL}/api/internal/jobs/source"

# ---------------------------------------------------------------------------
# Salary helpers
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"[\d,]+")

def _clean_num(s: str) -> int | None:
    """Strip commas and return int, or None if not parseable."""
    s = s.replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def parse_salary(raw: str) -> tuple[int | None, int | None]:
    """
    Parse a raw salary string into (salary_min, salary_max) in LAK/month.

    Examples handled:
      "3,000,000 - 5,000,000 LAK"   -> (3000000, 5000000)
      "5000000 kip"                  -> (5000000, None)
      "$500 - $800"                  -> (None, None)   # USD — skip
      ""                             -> (None, None)
    """
    if not raw:
        return None, None

    # Reject USD / THB / non-LAK currencies
    if re.search(r"[$€£฿]|USD|THB|EUR", raw, re.I):
        return None, None

    nums = _NUM_RE.findall(raw)
    if not nums:
        return None, None

    values = [_clean_num(n) for n in nums if _clean_num(n) is not None]

    # Sanity: LAK monthly salary should be between 500k and 500M
    values = [v for v in values if 500_000 <= v <= 500_000_000]

    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None

    low, high = min(values[0], values[1]), max(values[0], values[1])
    return low, high


# ---------------------------------------------------------------------------
# POST helper
# ---------------------------------------------------------------------------

def post_batch(jobs: list[dict], dry_run: bool = False) -> None:
    """
    Post a list of job dicts to the Job365 sourcing endpoint.

    Each dict should match the /api/internal/jobs/source request body contract.
    Skips jobs missing required fields (title, companyName, location, description).
    """
    if not jobs:
        return

    required = ("title", "companyName", "location", "description")

    for job in jobs:
        missing = [f for f in required if not job.get(f)]
        if missing:
            log.warning("Skipping job — missing required fields: %s | job=%s", missing, job.get("sourceUrl"))
            continue

        if dry_run:
            log.info("[DRY-RUN] Would post: %s @ %s", job.get("title"), job.get("companyName"))
            continue

        if not JOB365_SOURCING_TOKEN:
            log.error("JOB365_SOURCING_TOKEN is not set — cannot post.")
            return

        headers = {
            "Authorization": f"Bearer {JOB365_SOURCING_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(ENDPOINT, json=job, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                log.info("Posted: %s @ %s", job.get("title"), job.get("companyName"))
            elif resp.status_code == 409:
                log.debug("Duplicate (skipped): %s", job.get("sourceUrl"))
            else:
                log.warning("HTTP %s posting %s: %s", resp.status_code, job.get("sourceUrl"), resp.text[:200])
        except requests.RequestException as exc:
            log.error("Request error posting %s: %s", job.get("sourceUrl"), exc)
