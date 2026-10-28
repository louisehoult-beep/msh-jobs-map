"""
SRG (www.srgtalent.com) adapter.

SRG's sitemap lists per-job pages (/jobs/<id>-<slug>), so the generic crawler
discovers them with job_url_pattern "/jobs/\\d". The /jobs listing itself is a
client-side widget and is NOT used. Each job page does carry a schema.org
JobPosting, but nested under a WebPage node as "mainEntity", which the generic
extract_jobpostings() does not descend into. parse() unwraps it.
"""
import json
import re


def _walk(node, out):
    if isinstance(node, list):
        for n in node:
            _walk(n, out)
    elif isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            out.append(node)
        for key in ("mainEntity", "@graph"):
            if key in node:
                _walk(node[key], out)


KEEP_COUNTRIES = {"united kingdom", "uk", "gb", "ireland", "republic of ireland", "ie"}


def _tidy(posting: dict) -> dict | None:
    """Drop non-UK/Ireland roles (SRG's sitemap also lists US jobs) and collapse
    the street/locality/region repeats SRG fills in ("Aberdeen, Aberdeen, Aberdeen")."""
    loc = posting.get("jobLocation")
    addr = loc.get("address") if isinstance(loc, dict) else None
    if isinstance(addr, dict):
        country = str(addr.get("addressCountry") or "").strip().lower()
        if country and country not in KEEP_COUNTRIES:
            return None
        addr = dict(addr)
        loc_name = str(addr.get("addressLocality") or "").strip().lower()
        for k in ("streetAddress", "addressRegion"):
            if str(addr.get(k) or "").strip().lower() == loc_name:
                addr[k] = ""
        posting = dict(posting, jobLocation=dict(loc, address=addr))
    return posting


def parse(html: str, url: str) -> list[dict]:
    out: list[dict] = []
    for block in re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I
    ):
        try:
            _walk(json.loads(block.strip()), out)
        except Exception:
            continue
    return [t for t in (_tidy(p) for p in out) if t]
