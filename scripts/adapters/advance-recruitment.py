"""
Advance Recruitment (www.advancerecruitment.net) adapter.

The site is a Next.js app with no JobPosting JSON-LD and no job pages in the
sitemap. Its /cm/jobs search page, however, is server-rendered with the full
result set (title, description, UK region, salary text, post/expiry dates) in
the page's __NEXT_DATA__ JSON, 8 results per page, paged with ?page=N (0-based).
So list_jobs() reads those pages through the robots-honouring Host fetch and
emits JobPosting-shaped dicts. Each job's public page is /careers/<seoTitle>.

Fields not published are left out, never invented. The client employer is
anonymised by the agency, so hiringOrganization is omitted (the crawler then
attributes the listing to the recruiter).
"""
import json
import re

BASE = "https://www.advancerecruitment.net"
LIST_PATH = "/cm/jobs"
MAX_PAGES = 25


def _next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _val(fv: dict, key: str):
    v = (fv.get(key) or {}).get("value")
    if isinstance(v, str):
        v = v.strip()
        if v in ("", "-"):
            return None
    return v


def _salary(text: str | None):
    """Base salary from text like '£27,000 - £30,000' or '£50,000 + £23k commission'.
    Only the figures before any '+' are base salary. Returns None if no clear £ figure."""
    if not text:
        return None
    base = text.split("+")[0]
    nums = [float(n.replace(",", "")) for n in re.findall(r"£\s*([\d,]{4,})", base)]
    if not nums:
        return None
    return {"@type": "MonetaryAmount", "currency": "GBP",
            "value": {"@type": "QuantitativeValue", "minValue": min(nums[:2]),
                      "maxValue": max(nums[:2]), "unitText": "YEAR"}}


def item_to_posting(item: dict) -> dict | None:
    fv = item.get("fieldValues") or {}
    title = _val(fv, "title")
    seo = item.get("seoTitle")
    if not title or not seo or item.get("expired") or _val(fv, "draft") is True:
        return None
    # "International" is the site's non-UK bucket (e.g. a Germany-based role).
    if (_val(fv, "location") or "").lower() == "international":
        return None
    posting = {
        "url": f"{BASE}/careers/{seo}",
        "identifier": str(item.get("id")),
        "title": title,
        "description": _val(fv, "description") or _val(fv, "sdescr") or "",
        "datePosted": _val(fv, "post_date"),
        "validThrough": _val(fv, "expiration_date"),
        "employmentType": _val(fv, "job_type"),
        "industry": _val(fv, "sector"),
        # 'location' is the site's UK region selector (e.g. "Yorkshire",
        # "North Thames", "Scotland"); town_city is free text and unreliable.
        "jobLocation": _val(fv, "location") or "",
    }
    # The agency tags a vacancy with several UK regions by posting it once per
    # region (same ref + title, same text). Keep the ref so list_jobs can collapse them.
    posting["_ref"] = str(_val(fv, "ref") or "")
    sal = _salary(_val(fv, "exact_salary"))
    if sal:
        posting["baseSalary"] = sal
    return posting


def parse_results(html: str):
    """(postings, site total, items on page) from one /cm/jobs page."""
    sr = (((_next_data(html).get("props") or {}).get("pageProps") or {}).get("searchResult")) or {}
    items = sr.get("items") or []
    out = [p for p in (item_to_posting(i) for i in items) if p]
    return out, int(sr.get("total") or 0), len(items)


def list_jobs(fetch, rec):
    postings, seen_items = [], 0
    for page in range(MAX_PAGES):
        url = f"{BASE}{LIST_PATH}" + (f"?page={page}" if page else "")
        status, html = fetch(url, accept="text/html")
        if status != 200 or not html:
            break
        got, total, n_items = parse_results(html)
        postings.extend(got)
        seen_items += n_items
        if n_items == 0 or seen_items >= total:
            break
    out, seen = [], set()
    for p in postings:
        key = (p["_ref"], p["title"]) if p["_ref"] else p["url"]
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out
