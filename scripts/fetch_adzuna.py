"""
Fetch UK medical-sales / clinical-support listings from the official Adzuna
Job Search API (https://developer.adzuna.com/) — aggregates postings across
many UK boards into one structured feed.

Requires env vars ADZUNA_APP_ID and ADZUNA_APP_KEY. Free tier: 1,000
calls/month — this script paginates modestly (max 3 pages per keyword) to
stay well inside that.

If the keys aren't set, this returns an empty list rather than raising, so
the rest of the pipeline can still be exercised locally against fixtures.
"""
import json
import os
import urllib.parse
import urllib.request

BASE_URL = "https://api.adzuna.com/v1/api/jobs/gb/search"
# This one IS capped, and not by choice: the free tier allows 1,000 calls a
# MONTH. 8 keywords x 4 pages = 32 calls/day = 960/month, which is the most
# we can take without the source cutting out entirely partway through a month.
# Reed (uncapped) and the recruiter sites (uncapped) carry the volume; Adzuna
# overlaps them heavily anyway, so dedupe removes most of what it adds.
MAX_PAGES_PER_KEYWORD = 4
RESULTS_PER_PAGE = 50

# Budget note: the free tier allows 1,000 calls/month ~= 33/day. At 3 pages a
# keyword that is 8 keywords/day = 720/month, leaving headroom.
# The previous phrases were all multi-word ANDs and returned almost nothing
# ("nurse advisor medical device" matched 0). These are broader; the two-gate
# classifier is what removes the noise, not the search term.
SEARCH_KEYWORDS = [
    "medical sales",
    "medical device",
    "territory manager",
    "clinical specialist",
    "pharmaceutical sales",
    "healthcare sales",
    "surgical sales",
    "medical representative",
]


def _creds() -> tuple[str, str] | None:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return None
    return app_id, app_key


def _request_page(keyword: str, page: int, app_id: str, app_key: str) -> list[dict]:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": keyword,
        "results_per_page": str(RESULTS_PER_PAGE),
        "content-type": "application/json",
    }
    url = f"{BASE_URL}/{page}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[fetch_adzuna] keyword '{keyword}' page {page} failed: {exc}")
        return []
    return body.get("results", [])


def fetch_adzuna_listings() -> list[dict]:
    creds = _creds()
    if not creds:
        return []
    app_id, app_key = creds

    raw: list[dict] = []
    for kw in SEARCH_KEYWORDS:
        for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
            results = _request_page(kw, page, app_id, app_key)
            if not results:
                break
            raw.extend(results)

    normalised = []
    for job in raw:
        company = (job.get("company") or {}).get("display_name", "")
        location = (job.get("location") or {}).get("display_name", "")
        normalised.append(
            {
                "source": "adzuna",
                "source_id": str(job.get("id")),
                "title": job.get("title", ""),
                "company": company,
                "location_text": location,
                "description": job.get("description", "") or "",
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "contract_type": job.get("contract_type"),
                "posted_date": job.get("created"),
                "url": job.get("redirect_url"),
            }
        )
    return normalised
