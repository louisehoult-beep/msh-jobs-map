"""
Fetch UK medical-sales / clinical-support listings from the official Reed
Jobseeker API (https://www.reed.co.uk/developers/jobseeker).

Auth: HTTP Basic, API key as the username, blank password.
Requires env var REED_API_KEY.

If the key isn't set, this returns an empty list rather than raising, so
the rest of the pipeline (classify/dedupe/geocode/verify) can still be
exercised locally against fixtures without live credentials.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

SEARCH_URL = "https://www.reed.co.uk/api/1.0/search"

# Broad net — the sector/title gates in classify.py do the real filtering.
# Reed's own keyword search just needs to be wide enough not to miss things.
SEARCH_KEYWORDS = [
    "medical sales",
    "territory manager medical",
    "clinical sales specialist",
    "medical device sales",
    "pharmaceutical sales",
    "clinical nurse advisor",
    "product specialist medical device",
]


def _api_key() -> str | None:
    return os.environ.get("REED_API_KEY")


def _request(keyword: str, page_size: int = 100) -> list[dict]:
    key = _api_key()
    if not key:
        return []

    params = {"keywords": keyword, "resultsToTake": str(page_size)}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    auth = base64.b64encode(f"{key}:".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[fetch_reed] keyword '{keyword}' failed: {exc}")
        return []

    return body.get("results", [])


def fetch_reed_listings() -> list[dict]:
    """Returns a list of raw listings normalised to the pipeline's common shape."""
    raw: list[dict] = []
    for kw in SEARCH_KEYWORDS:
        raw.extend(_request(kw))

    normalised = []
    for job in raw:
        normalised.append(
            {
                "source": "reed",
                "source_id": str(job.get("jobId")),
                "title": job.get("jobTitle", ""),
                "company": job.get("employerName", ""),
                "location_text": job.get("locationName", ""),
                "description": job.get("jobDescription", "") or "",
                "salary_min": job.get("minimumSalary"),
                "salary_max": job.get("maximumSalary"),
                "contract_type": "Permanent" if job.get("permanent") else (
                    "Contract" if job.get("contractType") else None
                ),
                "posted_date": job.get("date"),
                "url": job.get("jobUrl"),
            }
        )
    return normalised
