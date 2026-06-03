"""
Shared helper for posting scraped jobs to the Job365 internal API.
Usage:
    from scripts.post import post_job
    result = post_job(payload)
"""
import os
import sys
import time
import json
import logging
import requests

API_BASE = os.getenv("JOB365_BASE_URL", "https://job365.ai")
ENDPOINT = f"{API_BASE}/api/internal/jobs/source"
TOKEN_ENV = "JOB365_SOURCING_TOKEN"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REQUIRED_FIELDS = {"title", "companyName", "location", "description", "sourceAttribution"}
VALID_TYPES = {"FULL_TIME", "PART_TIME", "CONTRACT", "TEMPORARY", "INTERNSHIP", "FREELANCE"}


def _get_token() -> str:
    token = os.getenv(TOKEN_ENV)
    if not token:
        raise EnvironmentError(f"{TOKEN_ENV} is not set — cannot post jobs")
    return token


def _validate(payload: dict) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not payload.get(field):
            errors.append(f"missing required field: {field}")
    if len(payload.get("description", "")) < 20:
        errors.append("description must be at least 20 characters")
    if "type" in payload and payload["type"] not in VALID_TYPES:
        errors.append(f"invalid type '{payload['type']}'; must be one of {VALID_TYPES}")
    return errors


def post_job(payload: dict, dry_run: bool = False) -> dict:
    """
    Post a single job to the Job365 API.

    Returns a result dict:
        {"status": 201|409|422|..., "id": "...", "slug": "...", "error": "..."}

    Raises on 401 (token invalid) or network errors.
    """
    errors = _validate(payload)
    if errors:
        raise ValueError(f"Payload validation failed: {'; '.join(errors)}")

    if dry_run:
        log.info("[DRY-RUN] Would post: %s @ %s", payload.get("title"), payload.get("companyName"))
        return {"status": "dry_run", "payload": payload}

    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Job365-Scraper/1.0 (+https://job365.ai)",
    }

    resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=15)

    if resp.status_code == 401:
        log.error("AUTH FAILURE — JOB365_SOURCING_TOKEN is invalid or expired. Alert ops.")
        raise PermissionError("401 Unauthorized — rotate JOB365_SOURCING_TOKEN immediately")

    body = {}
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code == 201:
        log.info("POSTED id=%s slug=%s title=%r", body.get("id"), body.get("slug"), payload["title"])
    elif resp.status_code == 409:
        log.info("SKIP (duplicate) id=%s title=%r", body.get("id"), payload["title"])
    else:
        log.warning("Unexpected %s for %r: %s", resp.status_code, payload["title"], body)

    return {"status": resp.status_code, **body}


def post_batch(payloads: list[dict], delay_seconds: float = 2.0, dry_run: bool = False) -> list[dict]:
    """Post a list of jobs with a polite delay between each."""
    results = []
    for i, payload in enumerate(payloads):
        try:
            result = post_job(payload, dry_run=dry_run)
            results.append(result)
        except PermissionError:
            log.error("Stopping batch — token auth failed on item %d", i)
            sys.exit(1)
        except ValueError as e:
            log.warning("Skipping item %d — %s", i, e)
            results.append({"status": "validation_error", "error": str(e), "index": i})
        if i < len(payloads) - 1:
            time.sleep(delay_seconds)
    return results


if __name__ == "__main__":
    # Quick smoke-test (dry run)
    sample = {
        "title": "Test Engineer",
        "companyName": "ACME Corp",
        "location": "Vientiane",
        "description": "Looking for a test engineer with Python skills.",
        "sourceAttribution": "test",
        "type": "FULL_TIME",
    }
    result = post_job(sample, dry_run=True)
    print(json.dumps(result, indent=2))
