"""
Evolve Selection (www.evolveselection.com) adapter.

Why an adapter: the sitemap is stale (3,000+ job URLs last modified 2024-2025,
mostly expired) and the old "/job" pattern matched 6,020 non-vacancy URLs. The
live vacancies are only reachable through the site's browse-view listing pages,
which load 9 roles at a time through a GET "load more" endpoint
(?tmpl=component&layout=ajax&limitstart=N). Detail pages DO carry a usable
schema.org JobPosting block, so we only need to (1) walk the listing pages to
find live detail URLs and (2) read the JSON-LD from each detail page.

recruiters.json supplies "listing_pages": paths of browse-view listings, e.g.
"/browse-view/healthcare/medtech/jobs". Requests go through the robots-honouring
rate-limited fetch() handed in by the crawler.
"""
import json
import re
import urllib.parse
from html import unescape

PAGE_SIZE = 9
MAX_LIST_PAGES = 40          # 360 roles per listing: safety stop only
JOB_HREF = re.compile(r'href="(/job-search/\d+-[^"]+/job)"')


def _abs(domain: str, href: str) -> str:
    href = unescape(href)
    # Non-ASCII dashes appear in slugs; urllib cannot send them raw.
    return "https://" + domain + urllib.parse.quote(href, safe="/%-_.~")


def job_links(html: str) -> list[str]:
    seen, out = set(), []
    for h in JOB_HREF.findall(html or ""):
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def parse(html: str, url: str) -> list[dict]:
    """Detail page -> [JobPosting dict] from its ld+json block, with url."""
    out = []
    for block in re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", re.S | re.I
    ):
        try:
            d = json.loads(block.strip(), strict=False)
        except Exception:
            continue
        for node in (d if isinstance(d, list) else [d]):
            if isinstance(node, dict) and node.get("@type") == "JobPosting" and node.get("title"):
                node = dict(node)
                node["url"] = url
                out.append(node)
    return out


NON_UK = {"usa", "republic of ireland"}


def is_uk(posting: dict) -> bool:
    """False when every stated region is outside the UK (the site labels
    "USA" and "Republic Of Ireland" roles with a ", UK" suffix). A role with
    no stated region is kept."""
    loc = posting.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    addr = loc.get("address") if isinstance(loc, dict) else None
    region = addr.get("addressRegion") if isinstance(addr, dict) else None
    if not region:
        return True
    parts = [x.strip().lower() for x in re.findall(r"([^,]+?),\s*UK\b", region, re.I)] or [region.strip().lower()]
    return not parts or any(p not in NON_UK for p in parts)


def list_jobs(fetch, rec: dict) -> list[dict]:
    domain = rec["domain"]
    pages = rec.get("listing_pages") or ["/browse-view/healthcare/medtech/jobs"]
    hrefs: list[str] = []
    for path in pages:
        base = _abs(domain, path)
        known = set(hrefs)
        for n in range(MAX_LIST_PAGES):
            url = base if n == 0 else f"{base}?tmpl=component&layout=ajax&limitstart={n * PAGE_SIZE}"
            status, html = fetch(url)
            if status != 200 or not html:
                break
            new = [h for h in job_links(html) if h not in known]
            if not new:
                break
            known.update(new)
            hrefs.extend(new)

    out = []
    for h in hrefs:
        url = _abs(domain, h)
        status, html = fetch(url)
        if status != 200 or not html:
            continue
        out.extend(p for p in parse(html, url)[:1] if is_uk(p))
    return out
