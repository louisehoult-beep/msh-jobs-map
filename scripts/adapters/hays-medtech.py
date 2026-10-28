"""
Hays (www.hays.co.uk) adapter, for the medtech / life-sciences sales scope.

Route: the sitemap Hays itself advertises in robots.txt
(https://www.hays.co.uk/sitemap/en-GB/job-sitemap.xml, ~6,000 jobs across ALL
sectors) -> per-job pages /job-detail/<slug>_<id> -> top-level schema.org
JobPosting JSON-LD. No login, key or token; the /jobs-search and /search?
widgets (disallowed in robots.txt) are never touched.

Two reasons this is a list_jobs adapter rather than the generic route:
  1. The sitemap wraps every <loc> in CDATA, which the generic
     collect_sitemap_urls() regex does not match.
  2. It is cross-sector. The job URL slug is the title plus location, so we
     apply the pipeline's own title gate (classify) to the slug BEFORE fetching,
     which takes ~6,000 URLs down to ~60 page fetches. The sector gate and full
     classification still run later in build_jobs_data, unchanged.
"""
import re
import sys
import urllib.parse
from pathlib import Path

SITEMAP = "https://www.hays.co.uk/sitemap/en-GB/job-sitemap.xml"
_LOC = re.compile(r"<loc>\s*(?:<!\[CDATA\[)?\s*(https://www\.hays\.co\.uk/job-detail/[^\s\]<]+)", re.I)


def _title_gate():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import classify
    return lambda text: bool(classify._SALES_RE.search(text) or classify._CLINICAL_SUPPORT_RE.search(text))


def slug_title(url: str) -> str:
    slug = url.split("/job-detail/", 1)[1].rsplit("_", 1)[0]
    return re.sub(r"\s+", " ", urllib.parse.unquote(slug).replace("-", " ")).strip()


def sitemap_urls(xml: str) -> list[str]:
    return list(dict.fromkeys(_LOC.findall(xml)))


# Hays is cross-sector and its sector label is on every JobPosting ("industry").
# The pipeline's sector gate alone let through Construction / Manufacturing /
# Staffing roles whose ad text merely mentions "healthcare", so keep only
# Hays' own health / pharma / life-science / device labels.
INDUSTRY_OK = re.compile(r"health|medic|pharma|life\s*sci|biotech|device", re.I)


def keep(posting: dict) -> bool:
    return bool(INDUSTRY_OK.search(str(posting.get("industry") or "")))


def _tidy_location(posting: dict) -> dict:
    loc = posting.get("jobLocation")
    addr = loc.get("address") if isinstance(loc, dict) else None
    if isinstance(addr, dict) and str(addr.get("addressRegion") or "").lower() == str(addr.get("addressLocality") or "").lower():
        posting = dict(posting, jobLocation=dict(loc, address=dict(addr, addressRegion="")))
    return posting


def list_jobs(fetch, rec):
    from crawl_recruiters import extract_jobpostings
    gate = _title_gate()
    status, xml = fetch(SITEMAP, "application/xml")
    if status != 200 or not xml:
        return []
    urls = [u for u in sitemap_urls(xml) if gate(slug_title(u))]
    out = []
    for u in urls:
        status, html = fetch(u, "text/html")
        if status != 200 or not html:
            continue
        postings = extract_jobpostings(html)
        if postings:
            if not keep(postings[0]):
                continue
            p = _tidy_location(dict(postings[0]))
            p["url"] = u
            out.append(p)
    return out
