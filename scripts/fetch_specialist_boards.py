"""
Specialist medical/pharma sales job boards (Zenopa, MedReps, BMS Performance,
eMedCareers, CHASE, etc.) — these carry the purest medical-sales-specific
and clinical-support listings, but none of them expose a public API or RSS
feed (checked 16/09/2026). Reaching them means crawling their own listing
pages directly.

NOT YET IMPLEMENTED. Before writing a scraper against any of these sites,
each one needs:
  1. Its robots.txt checked for a disallow on the listings path.
  2. Its Terms of Use checked for an explicit no-scraping clause.
  3. A conservative rate limit (this pipeline runs once a day — no reason
     to hit any site harder than a handful of requests per run) and a
     clearly-identifying User-Agent.

Reed + Adzuna (fetch_reed.py / fetch_adzuna.py) are both official APIs and
already cover general UK job-board volume. This module exists so the
pipeline's shape is ready — build_jobs_data.py calls it and it currently
returns an empty list, which is the correct behaviour until each site has
been checked and a scraper written for it.
"""


def fetch_specialist_board_listings() -> list[dict]:
    # TODO: implement per-site, only after the robots.txt / ToS check above
    # has been done for that specific site. See module docstring.
    return []
