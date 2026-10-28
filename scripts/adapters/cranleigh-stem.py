"""
Adapter for Cranleigh STEM (cranleighstem.co.uk, bespoke CMS).

The site publishes no schema.org JobPosting JSON-LD, so parse() reads the
detail page's own markup (div.single-job-header + div.single-job-body):

  <h2>title</h2>  <h3>sector label</h3>  <h4 class="location">..</h4>
  <h4 class="salary">..</h4>  <span class="job-type permanent">  Job Ref

Discovery needs no adapter: /opportunities (paged ?page=2, ?page=3) links
every vacancy as /opportunities/<slug>-<ref>. See proposed/cranleigh-stem.json.
The sector label ("Medical Devices", "Animal Health", "Biotech" ...) is real
site data; it is passed as `industry` and also put at the start of the
description so the classifier's sector gate can see it.
"""
import re
from html import unescape


def _txt(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", unescape(s)).strip()


def _salary_values(block: str):
    """£28000k – £35000k style: the site appends a stray 'k' to full figures."""
    nums = []
    for m in re.finditer(r"£\s*([\d,]+(?:\.\d+)?)\s*(k?)", block, re.I):
        v = float(m.group(1).replace(",", ""))
        if m.group(2) and v < 1000:
            v *= 1000
        nums.append(v)
    return nums


def parse(html: str, url: str):
    m = re.search(r'<div class="single-job-header.*?</div>', html, re.S)
    if not m:
        return []
    head = m.group(0)
    title = re.search(r"<h2>(.*?)</h2>", head, re.S)
    if not title or not _txt(title.group(1)):
        return []
    sector = re.search(r"<h3>(.*?)</h3>", head, re.S)
    loc = re.search(r'<h4 class="location">(.*?)</h4>', head, re.S)
    sal = re.search(r'<h4 class="salary">(.*?)</h4>', head, re.S)
    jtype = re.search(r'<span class="job-type[^"]*">(.*?)</span>', head, re.S)
    ref = re.search(r"Job Ref:</strong>\s*([^<\s]+)", head)
    body = re.search(r'<div class="single-job-body[^>]*>(.*?)\n\s*</div>\s*\n\s*<div class="single-job-footer', html, re.S)
    desc = _txt(body.group(1)) if body else ""
    desc = re.sub(r"^Description\s+", "", desc)
    sector_t = _txt(sector.group(1)) if sector else ""

    # The site also lists overseas roles under location "Rest of World"
    # (e.g. Mexico). The jobs map is UK-only, so these are not returned.
    if loc and _txt(loc.group(1)).lower() == "rest of world":
        return []

    posting = {
        "title": _txt(title.group(1)),
        "description": (f"Sector: {sector_t}. " if sector_t else "") + desc,
        "industry": sector_t or None,
        "employmentType": _txt(jtype.group(1)).upper() if jtype else None,
        "identifier": ref.group(1) if ref else None,
        "hiringOrganization": {"name": "Cranleigh STEM"},
    }
    if loc and _txt(loc.group(1)):
        posting["jobLocation"] = {"address": {"addressLocality": _txt(loc.group(1))}}
    if sal:
        nums = _salary_values(sal.group(1))
        if nums:
            posting["baseSalary"] = {"value": {"minValue": min(nums), "maxValue": max(nums)}}
    return [posting]
