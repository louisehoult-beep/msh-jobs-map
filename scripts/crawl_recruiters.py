"""
Recruiter-site crawler for the Medical Sales Hub jobs map.

Route: robots.txt -> sitemap -> job detail URLs -> schema.org/JobPosting
JSON-LD -> normalised listing.

Why this route rather than LinkedIn: recruiters publish JobPosting JSON-LD on
their own sites *deliberately*, so that Google for Jobs and other aggregators
can index them. It is the invited, documented, machine-readable route, it
carries richer fields than a scraped listing (salary min/max, employment type,
industry, posted date, structured location), and for UK medical sales it is
more complete than LinkedIn because agencies post everything to their own site
first and syndicate outwards afterwards.

Discipline built in, not bolted on:
  * robots.txt is fetched and honoured per host, every run.
  * One request at a time per host, with a delay between them.
  * A clearly-identifying User-Agent with a contact URL.
  * Sitemap <lastmod> drives incremental fetching — a daily run re-fetches
    only what changed, so we are not re-pulling thousands of unchanged pages.
"""
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).parent.parent
REGISTRY = ROOT / "recruiters.json"
CACHE = ROOT / "data" / "crawl-cache.json"

UA = "MedSalesHubBot/1.0 (+https://medsalesintelligencehub.co.uk; jobs aggregation for Hub members)"
TIMEOUT = 20
DELAY_SECONDS = 1.5          # between requests to the same host
# No per-site cap (Lou, 16/09/2026): if a recruiter role matches the gates it
# goes on the page. We crawl every job URL a site publishes. Politeness is
# handled by the 1.5s per-host delay, not by throwing matching roles away.
MAX_JOBS_PER_SITE = None
MAX_AGE_DAYS = 120           # a 4-month-old posting is almost always filled


def _get(url: str, accept: str = "*/*") -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


class Host:
    """Per-host robots.txt compliance and rate limiting."""

    def __init__(self, domain: str):
        self.domain = domain
        self.last_request = 0.0
        self.sitemaps = []
        self.rp = RobotFileParser()
        self.rp.set_url(f"https://{domain}/robots.txt")

        # Fetch robots.txt ourselves and hand the text to the parser, rather
        # than letting RobotFileParser.read() fetch it. Its internal fetch
        # uses Python's default User-Agent, which some of these sites block
        # outright — and on a 403 it sets disallow_all, so a site that
        # actually permits crawling reads as "everything forbidden".
        status, body = _get(f"https://{domain}/robots.txt", accept="text/plain")
        if status == 200 and body.strip():
            self.rp.parse(body.splitlines())
            self.robots_ok = True
            self.sitemaps = re.findall(r"(?i)^sitemap:\s*(\S+)", body, re.M)
        elif status == 404:
            # No robots.txt published = no stated restriction.
            self.robots_ok = False
        else:
            # Anything else (403, 5xx, network error): fail CLOSED. We do not
            # crawl a site whose rules we could not read.
            self.rp.disallow_all = True
            self.robots_ok = True

    def allowed(self, url: str) -> bool:
        if not self.robots_ok:
            return True  # no readable robots.txt = no stated restriction
        try:
            return self.rp.can_fetch(UA, url)
        except Exception:
            return True

    def fetch(self, url: str, accept: str = "*/*") -> tuple[int | None, str]:
        if not self.allowed(url):
            return "BLOCKED_BY_ROBOTS", ""
        elapsed = time.time() - self.last_request
        if elapsed < DELAY_SECONDS:
            time.sleep(DELAY_SECONDS - elapsed)
        self.last_request = time.time()
        return _get(url, accept)


def collect_sitemap_urls(host: Host, max_child_maps: int = 200) -> list[dict]:
    """Return [{loc, lastmod}] from the host's sitemap(s), descending one level."""
    seeds = host.sitemaps or [
        f"https://{host.domain}/sitemap.xml",
        f"https://{host.domain}/sitemap_index.xml",
    ]
    entries: list[dict] = []
    child_maps: list[str] = []

    for sm in seeds[:3]:
        status, body = host.fetch(sm, accept="application/xml")
        if status != 200 or not body:
            continue
        for m in re.finditer(r"<(?:url|sitemap)>(.*?)</(?:url|sitemap)>", body, re.S):
            block = m.group(1)
            loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
            if not loc:
                continue
            url = loc.group(1)
            lastmod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", block)
            rec = {"loc": url, "lastmod": lastmod.group(1) if lastmod else None}
            if url.endswith(".xml") or url.endswith(".xml.gz"):
                child_maps.append(url)
            else:
                entries.append(rec)

    for child in child_maps[:max_child_maps]:
        status, body = host.fetch(child, accept="application/xml")
        if status != 200 or not body:
            continue
        for m in re.finditer(r"<url>(.*?)</url>", body, re.S):
            block = m.group(1)
            loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
            if not loc:
                continue
            lastmod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", block)
            entries.append({"loc": loc.group(1), "lastmod": lastmod.group(1) if lastmod else None})

    return entries


def collect_listing_page_urls(host: Host, rec: dict, pattern: re.Pattern) -> list[dict]:
    """
    Fallback discovery for sites whose job pages aren't in the sitemap
    (Zenopa, for one): crawl the configured listing page(s) and pull job
    detail links straight out of the HTML.
    """
    entries: list[dict] = []
    for path in rec.get("listing_pages", []):
        url = urllib.parse.urljoin(f"https://{host.domain}/", path)
        status, html = host.fetch(url, accept="text/html")
        if status != 200 or not html:
            continue
        for href in re.findall(r'href=["\']([^"\']+)["\']', html):
            full = urllib.parse.urljoin(url, href).split("?")[0].split("#")[0]
            netloc = urllib.parse.urlparse(full).netloc.replace("www.", "")
            if netloc != host.domain.replace("www.", ""):
                continue
            if pattern.search(full):
                entries.append({"loc": full, "lastmod": None})
    return list({e["loc"]: e for e in entries}.values())


def extract_jobpostings(html: str) -> list[dict]:
    out = []
    for block in re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I
    ):
        try:
            parsed = json.loads(block.strip())
        except Exception:
            continue
        stack = parsed if isinstance(parsed, list) else [parsed]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            if isinstance(node.get("@graph"), list):
                stack.extend(node["@graph"])
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if "JobPosting" in types:
                out.append(node)
    return out


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    # Unescape repeatedly: some feeds are double-encoded, so "&amp;#8211;"
    # needs two passes or a literal "&#8211;" ends up rendered on the page
    # (23 BMS Performance titles did exactly that).
    text = str(value)
    for _ in range(3):
        new = unescape(text)
        if new == text:
            break
        text = new
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _location_text(posting: dict) -> str:
    loc = posting.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return _clean(loc)
    addr = loc.get("address")
    if isinstance(addr, list):
        addr = addr[0] if addr else None
    if not isinstance(addr, dict):
        return _clean(addr) or _clean(loc.get("name"))
    parts = [
        addr.get("streetAddress"), addr.get("addressLocality"),
        addr.get("addressRegion"), addr.get("postalCode"),
    ]
    return ", ".join(_clean(p) for p in parts if _clean(p))


def _salary(posting: dict) -> tuple[float | None, float | None]:
    base = posting.get("baseSalary")
    if isinstance(base, list):
        base = base[0] if base else None
    if not isinstance(base, dict):
        return None, None
    val = base.get("value")
    if isinstance(val, dict):
        lo, hi = val.get("minValue"), val.get("maxValue")
        single = val.get("value")
        if lo is None and hi is None and single is not None:
            lo = hi = single
    else:
        lo = hi = val

    def num(x):
        if x is None:
            return None
        try:
            return float(str(x).replace(",", "").replace("£", "").strip())
        except Exception:
            return None

    return num(lo), num(hi)


def normalise(posting: dict, url: str, recruiter: str) -> dict:
    org = posting.get("hiringOrganization")
    if isinstance(org, list):
        org = org[0] if org else None
    company = _clean(org.get("name")) if isinstance(org, dict) else _clean(org)

    # Agencies commonly anonymise the end client ("Private Company", or a
    # category string). Keep whatever they state, but always record which
    # recruiter the listing came from so the page can attribute it.
    lo, hi = _salary(posting)

    return {
        "source": f"recruiter:{recruiter}",
        "recruiter": recruiter,
        "source_id": _clean(posting.get("identifier")) or url.rstrip("/").split("/")[-1],
        "title": _clean(posting.get("title")),
        "company": company or recruiter,
        "location_text": _location_text(posting),
        "description": _clean(posting.get("description"))[:6000],
        "salary_min": lo,
        "salary_max": hi,
        "contract_type": _clean(posting.get("employmentType")) or None,
        "posted_date": _clean(posting.get("datePosted")) or None,
        "valid_through": _clean(posting.get("validThrough")) or None,
        "industry": _clean(posting.get("industry")) or None,
        "url": url,
    }


def _is_recent(posted: str | None) -> bool:
    if not posted:
        return True
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", posted)
    if not m:
        return True
    from datetime import date
    y, mo, d = (int(g) for g in m.groups())
    try:
        age = (date.today() - date(y, mo, d)).days
    except ValueError:
        return True
    return age <= MAX_AGE_DAYS


def crawl_recruiter(rec: dict, cache: dict) -> tuple[list[dict], dict]:
    name, domain = rec["name"], rec["domain"]
    pattern = re.compile(rec["job_url_pattern"], re.I)

    report = {"recruiter": name, "domain": domain}
    host = Host(domain)

    entries = collect_sitemap_urls(host)
    job_entries = [e for e in entries if pattern.search(e["loc"])]
    job_entries = list({e["loc"]: e for e in job_entries}.values())
    report["job_urls_in_sitemap"] = len(job_entries)

    # Additive, not fallback-only: some sites list only the job archive page
    # in their sitemap and expose individual vacancies on the listing page.
    if rec.get("listing_pages"):
        from_listing = collect_listing_page_urls(host, rec, pattern)
        report["job_urls_from_listing_pages"] = len(from_listing)
        job_entries = list({e["loc"]: e for e in (job_entries + from_listing)}.values())

    site_cache = cache.setdefault(domain, {})
    listings, fetched, skipped, blocked, empty = [], 0, 0, 0, 0

    for entry in (job_entries if MAX_JOBS_PER_SITE is None else job_entries[:MAX_JOBS_PER_SITE]):
        url, lastmod = entry["loc"], entry["lastmod"]
        cached = site_cache.get(url)

        # Incremental: skip anything whose sitemap lastmod hasn't moved.
        if cached and lastmod and cached.get("lastmod") == lastmod and cached.get("listing"):
            listings.append(cached["listing"])
            skipped += 1
            continue

        status, html = host.fetch(url, accept="text/html")
        if status == "BLOCKED_BY_ROBOTS":
            blocked += 1
            continue
        if status != 200 or not html:
            continue
        fetched += 1

        postings = extract_jobpostings(html)
        if not postings:
            site_cache[url] = {"lastmod": lastmod, "listing": None, "no_jsonld": True}
            continue

        listing = normalise(postings[0], url, name)
        if not listing["title"]:
            # Some sites publish a JobPosting skeleton with every field empty
            # (Mediplacements does exactly this). The block is present, so a
            # naive "has JobPosting?" check calls the site usable when it
            # carries no data at all. Record it so it shows up in the report
            # as an empty-schema site rather than a silent zero.
            site_cache[url] = {"lastmod": lastmod, "listing": None, "empty_jsonld": True}
            empty += 1
            continue
        if not _is_recent(listing["posted_date"]):
            site_cache[url] = {"lastmod": lastmod, "listing": None, "stale": True}
            continue

        site_cache[url] = {"lastmod": lastmod, "listing": listing}
        listings.append(listing)

    report.update({
        "fetched": fetched, "from_cache": skipped,
        "blocked_by_robots": blocked, "empty_jsonld": empty,
        "listings": len(listings),
    })
    return listings, report


def load_registry() -> list[dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def fetch_recruiter_listings(verbose: bool = True) -> tuple[list[dict], list[dict]]:
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    all_listings, reports = [], []
    for rec in load_registry():
        if not rec.get("enabled", True):
            continue
        if verbose:
            print(f"  crawling {rec['name']} ({rec['domain']}) ...", flush=True)
        try:
            listings, report = crawl_recruiter(rec, cache)
        except Exception as exc:
            report = {"recruiter": rec["name"], "domain": rec["domain"], "error": repr(exc)}
            listings = []
        all_listings.extend(listings)
        reports.append(report)
        if verbose:
            print(f"     {report}", flush=True)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=2)[:40_000_000], encoding="utf-8")
    return all_listings, reports


def main():
    listings, reports = fetch_recruiter_listings()
    print(f"\nTotal listings from recruiter sites: {len(listings)}")
    out = ROOT / "data" / "recruiter-listings.json"
    out.write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
