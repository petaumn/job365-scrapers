import os

BASE_URL: str = os.environ.get("JOB365_BASE_URL", "https://job365.ai")
TOKEN: str = os.environ.get("JOB365_SOURCING_TOKEN", "")
ENDPOINT: str = f"{BASE_URL}/api/internal/jobs/source"
