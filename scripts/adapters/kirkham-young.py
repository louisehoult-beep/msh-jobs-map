"""Kirkham Young (www.kirkhamyoung.co.uk) adapter.

The site has no per-job pages, no JobPosting JSON-LD and no job URLs in its
sitemaps. Every live role is server-rendered as an <article class="jbb-card">
on https://www.kirkhamyoung.co.uk/careers/ (all roles on one page, no
pagination). list_jobs() fetches that one page and parses the cards.
"""
import re
from html import unescape

LISTING = "https://www.kirkhamyoung.co.uk/careers/"


def _text(fragment: str) -> str:
    t = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", unescape(unescape(t))).strip()


def _field(card: str, cls: str) -> str:
    m = re.search(r'<div class="%s">(.*?)</div>' % cls, card, re.S)
    if not m:
        return ""
    return _text(re.sub(r'<span class="label">.*?</span>', "", m.group(1), flags=re.S))


def _iso(d: str):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", d.strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse_listing(html: str) -> list:
    start = html.find('id="jbb-results"')
    if start < 0:
        return []
    out = []
    for card in re.findall(r'<article class="jbb-card.*?</article>', html[start:], re.S):
        title = _text((re.search(r'<div class="job-title"><h3>(.*?)</h3>', card, re.S) or [None, ""])[1])
        ref = _field(card, "job-ref")
        if not title or not ref:
            continue
        dm = re.search(r'<div class="job-description">(.*?)</div><div class="job-apply">', card, re.S)
        out.append({
            "url": f"{LISTING}#{ref}",
            "identifier": ref,
            "title": title,
            "jobLocation": _field(card, "job-location"),
            "datePosted": _iso(_field(card, "job-posted")),
            "description": _text(dm.group(1)) if dm else "",
            "industry": _field(card, "job-sector") or None,
            "hiringOrganization": "Kirkham Young",
        })
    return out


def list_jobs(fetch, rec):
    status, html = fetch(LISTING, accept="text/html")
    if status != 200 or not html:
        return []
    return parse_listing(html)
