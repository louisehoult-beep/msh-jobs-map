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
    "medical representative",
    "theatre sales",
    "surgical sales",
    "healthcare sales",
    "clinical specialist medical device",
]


def _api_key() -> str | None:
    return os.environ.get("REED_API_KEY")


# Reed caps a single response at 100. Without paging we were taking 565 of the
# 1,315 rows it actually holds for these keywords — "medical sales" alone has
# 754 and we saw 100 of them. Page until exhausted, bounded per keyword so a
# broad term cannot run away with the whole job.
PAGE_SIZE = 100
# No cap (Lou, 16/09/2026): page until Reed runs out. A matching role is not
# dropped because it happened to sit on page 5. HARD_STOP only exists so a
# pathological term cannot loop forever.
HARD_STOP = 5000


def _request(keyword: str) -> list[dict]:
    key = _api_key()
    if not key:
        return []
    auth = base64.b64encode(f"{key}:".encode("utf-8")).decode("ascii")

    collected: list[dict] = []
    skip = 0
    while skip < HARD_STOP:
        params = {
            "keywords": keyword,
            "resultsToTake": str(PAGE_SIZE),
            "resultsToSkip": str(skip),
        }
        url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"[fetch_reed] keyword '{keyword}' page skip={skip} failed: {exc}")
            break

        page = body.get("results", [])
        collected.extend(page)
        total = body.get("totalResults", 0)
        skip += PAGE_SIZE
        if len(page) < PAGE_SIZE or skip >= total:
            break

    return collected


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
