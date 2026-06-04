"""
lib/post.py — shared helpers for Job365 sourcing API.

Provides:
  post_job(payload, dry_run)   — POST a single job to /api/internal/jobs/source
  post_batch(jobs, dry_run)    — POST a list of job dicts with rate-limiting
  parse_salary                 — re-exported from lib.normalize for back-compat
"""
import logging
import os
import sys
import time

import requests

from lib.normalize import parse_salary  # noqa: F401 — re-exported for back-compat

log = logging.getLogger(__name__)

_BASE_URL = os.environ.get("JOB365_BASE_URL", "https://job365.ai")
_ENDPOINT = f"{_BASE_URL}/api/internal/jobs/source"

_REQUIRED = ("title", "companyName", "location", "description")


def _token() -> str:
    tok = os.environ.get("JOB365_SOURCING_TOKEN", "")
    if not tok:
        raise EnvironmentError("JOB365_SOURCING_TOKEN is not set — cannot post")
    return tok


def post_job(payload: dict, dry_run: bool = False) -> dict:
    """
    POST a single job dict to the Job365 sourcing endpoint.

    Returns {"status": 201|409|4xx, ...response body...}.
    Raises PermissionError on 401; raises EnvironmentError if token missing.
    """
    if dry_run:
        log.info("[DRY-RUN] Would post: %s @ %s", payload.get("title"), payload.get("companyName"))
        return {"status": "dry_run"}

    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    }

    resp = requests.post(_ENDPOINT, json=payload, headers=headers, timeout=15)

    if resp.status_code == 401:
        log.error("AUTH FAILURE — rotate JOB365_SOURCING_TOKEN immediately")
        raise PermissionError("401 Unauthorized")

    body: dict = {}
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code in (200, 201):
        log.info("POSTED id=%s slug=%s title=%r", body.get("id"), body.get("slug"), payload.get("title"))
    elif resp.status_code == 409:
        log.debug("DUPLICATE (skipped): %s", payload.get("sourceUrl"))
    else:
        log.warning("HTTP %s for %r: %s", resp.status_code, payload.get("title"), body)

    return {"status": resp.status_code, **body}


def post_batch(
    jobs: list[dict],
    delay_seconds: float = 1.0,
    dry_run: bool = False,
) -> list[dict]:
    """
    POST a list of job dicts with a polite delay between each request.

    Skips jobs missing required fields. Stops immediately on 401.
    """
    results: list[dict] = []
    for i, job in enumerate(jobs):
        missing = [f for f in _REQUIRED if not job.get(f)]
        if missing:
            log.warning(
                "Skipping job %d — missing fields: %s | url=%s",
                i, missing, job.get("sourceUrl"),
            )
            continue

        try:
            result = post_job(job, dry_run=dry_run)
            results.append(result)
        except PermissionError:
            log.error("Stopping batch — token auth failed at item %d", i)
            sys.exit(1)

        if i < len(jobs) - 1:
            time.sleep(delay_seconds)

    return results
