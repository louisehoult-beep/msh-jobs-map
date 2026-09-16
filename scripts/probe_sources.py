"""
Source-discovery probe for recruiter sites.

For each recruiter domain this checks, in the order we'd prefer to consume:
  1. robots.txt   — is the jobs path allowed at all?
  2. JSON-LD      — does a job page carry schema.org/JobPosting? (the format
                    site owners publish deliberately for Google for Jobs —
                    the cleanest and most stable thing to consume)
  3. RSS/XML feed — common WordPress/ATS feed paths
  4. JSON API     — common headless/ATS search endpoints
  5. Sitemap      — job URLs discoverable for a polite HTML parse fallback

Run:  python3 scripts/probe_sources.py
Writes a report to data/source-probe.json so the per-site adapters in
scripts/recruiters/ can be written against real findings, not guesses.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data" / "source-probe.json"

UA = "Mozilla/5.0 (compatible; MedSalesHubBot/1.0; +https://medsalesintelligencehub.co.uk)"
TIMEOUT = 15
POLITE_DELAY = 1.0  # seconds between requests to the same host

# UK medical sales / medical device / pharma specialist recruiters.
# jobs_path is the public listing page we'd crawl.
RECRUITERS = [
    {"name": "Zenopa", "domain": "zenopa.com", "jobs_path": "/job-search/"},
    {"name": "Evolve Selection", "domain": "evolveselection.com", "jobs_path": "/jobs/"},
    {"name": "BMS Performance", "domain": "bmsperformance.com", "jobs_path": "/jobs/"},
    {"name": "On Target Recruitment", "domain": "www.otrsales.co.uk", "jobs_path": "/jobs/"},
    {"name": "Advance Recruitment", "domain": "advancerecruitment.net", "jobs_path": "/jobs/"},
    {"name": "CHASE", "domain": "chasepeople.com", "jobs_path": "/jobs/"},
    {"name": "ID Search & Selection", "domain": "idsearchandselection.com", "jobs_path": "/jobs/"},
    {"name": "TRS Consulting", "domain": "www.trsconsulting.com", "jobs_path": "/jobs/"},
    {"name": "Cranleigh STEM", "domain": "cranleighstem.com", "jobs_path": "/jobs/"},
    {"name": "Clinical Professionals", "domain": "www.clinicalprofessionals.co.uk", "jobs_path": "/jobs/"},
    {"name": "Coburg Banks", "domain": "www.coburgbanks.co.uk", "jobs_path": "/jobs/"},
    {"name": "Star Medical", "domain": "starmedical.co.uk", "jobs_path": "/jobs/"},
]

FEED_CANDIDATES = [
    "/feed/", "/jobs/feed/", "/job/feed/", "/job-post/feed/", "/vacancies/feed/",
    "/jobs.rss", "/jobs.xml", "/job-feed.xml", "/rss/jobs",
]

JSON_CANDIDATES = [
    "/wp-json/wp/v2/job", "/wp-json/wp/v2/jobs", "/wp-json/wp/v2/vacancy",
    "/api/jobs", "/api/v1/jobs", "/jobs.json", "/api/job-search",
]


def get(url, want_bytes=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read()
            return r.status, r.headers.get("Content-Type", ""), (data if want_bytes else data.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, "", ""
    except Exception as e:
        return None, f"ERR:{type(e).__name__}", ""


def check_robots(domain, jobs_path):
    status, _, body = get(f"https://{domain}/robots.txt")
    if status != 200:
        return {"status": status, "jobs_path_allowed": None, "note": "no robots.txt"}
    disallowed = []
    active = False
    for line in body.splitlines():
        line = line.strip()
        if line.lower().startswith("user-agent:"):
            active = line.split(":", 1)[1].strip() == "*"
        elif active and line.lower().startswith("disallow:"):
            rule = line.split(":", 1)[1].strip()
            if rule:
                disallowed.append(rule)
    blocked = False
    for rule in disallowed:
        pattern = rule.replace("*", "")
        if pattern and jobs_path.startswith(pattern.rstrip("$")):
            blocked = True
    return {"status": 200, "jobs_path_allowed": not blocked, "disallow_rules": disallowed[:12]}


def find_jsonld_jobposting(html):
    """Return JobPosting objects found in JSON-LD, handling @graph and lists."""
    found = []
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I
    )
    for b in blocks:
        try:
            parsed = json.loads(b.strip())
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
            if "@graph" in node and isinstance(node["@graph"], list):
                stack.extend(node["@graph"])
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if "JobPosting" in types:
                found.append(node)
    return found


def discover_job_links(domain, html):
    """Find plausible individual job-detail URLs on a listing page."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
    out = []
    for h in hrefs:
        full = urllib.parse.urljoin(f"https://{domain}/", h)
        if urllib.parse.urlparse(full).netloc.replace("www.", "") != domain.replace("www.", ""):
            continue
        if re.search(r"/(job-post|job|jobs|vacancy|vacancies|position)/[^/]+/", full, re.I):
            if not re.search(r"/(jobs|vacancies)/?$", full, re.I):
                out.append(full.split("?")[0])
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def probe(rec):
    domain, jobs_path = rec["domain"], rec["jobs_path"]
    result = {"name": rec["name"], "domain": domain, "jobs_path": jobs_path}

    result["robots"] = check_robots(domain, jobs_path)
    time.sleep(POLITE_DELAY)

    status, ctype, html = get(f"https://{domain}{jobs_path}")
    result["jobs_page"] = {"status": status, "content_type": ctype.split(";")[0], "bytes": len(html)}

    job_links = discover_job_links(domain, html) if status == 200 else []
    result["job_links_found"] = len(job_links)
    result["sample_job_links"] = job_links[:3]

    # JSON-LD JobPosting on a real job detail page
    result["jsonld_jobposting"] = False
    result["jsonld_fields"] = []
    if job_links:
        time.sleep(POLITE_DELAY)
        s2, _, jobhtml = get(job_links[0])
        if s2 == 200:
            postings = find_jsonld_jobposting(jobhtml)
            if postings:
                result["jsonld_jobposting"] = True
                result["jsonld_fields"] = sorted(postings[0].keys())
        # listing pages sometimes carry JobPosting too
    if not result["jsonld_jobposting"] and status == 200:
        if find_jsonld_jobposting(html):
            result["jsonld_jobposting"] = "listing_page_only"

    # feeds
    feeds = []
    for path in FEED_CANDIDATES:
        time.sleep(0.3)
        s, ct, body = get(f"https://{domain}{path}")
        if s == 200 and ("xml" in ct.lower() or body.lstrip().startswith("<?xml") or "<rss" in body[:500].lower()):
            item_count = body.lower().count("<item")
            feeds.append({"path": path, "items": item_count})
    result["feeds"] = feeds

    # json endpoints
    apis = []
    for path in JSON_CANDIDATES:
        time.sleep(0.3)
        s, ct, body = get(f"https://{domain}{path}")
        if s == 200 and "json" in ct.lower():
            try:
                parsed = json.loads(body)
                n = len(parsed) if isinstance(parsed, list) else 1
                apis.append({"path": path, "records": n})
            except Exception:
                pass
    result["json_apis"] = apis

    # recommended route
    if result["jsonld_jobposting"] is True:
        route = "jsonld"
    elif apis:
        route = "json_api"
    elif feeds:
        route = "rss"
    elif job_links:
        route = "html_parse"
    else:
        route = "none_found"
    result["recommended_route"] = route
    return result


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    targets = [r for r in RECRUITERS if not only or only.lower() in r["domain"].lower()]

    results = []
    for rec in targets:
        print(f"probing {rec['name']} ({rec['domain']}) ...", flush=True)
        try:
            res = probe(rec)
        except Exception as exc:
            res = {"name": rec["name"], "domain": rec["domain"], "error": repr(exc)}
        results.append(res)
        print(f"   route={res.get('recommended_route')} jsonld={res.get('jsonld_jobposting')} "
              f"links={res.get('job_links_found')} feeds={len(res.get('feeds', []))} apis={len(res.get('json_apis', []))}",
              flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")

    routes = {}
    for r in results:
        routes.setdefault(r.get("recommended_route", "error"), []).append(r["name"])
    print("\nSummary by route:")
    for route, names in sorted(routes.items()):
        print(f"  {route:12} {len(names):2}  {', '.join(names)}")


if __name__ == "__main__":
    main()
