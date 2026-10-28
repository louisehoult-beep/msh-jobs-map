"""
Barrington James adapter.

Their job pages carry a schema.org JobPosting block, but it is hand-templated
and is NOT valid JSON: the description holds raw newlines inside the string, so
json.loads() raises "Invalid control character" and extract_jobpostings()
silently drops the page (49 of 70 vacancies on 2026-10-28, including the sales
roles). This adapter re-parses that same block leniently (strict=False).

Their location lives in jobLocation.address.addressCountry (locality/region are
usually blank), which the shared _location_text() ignores. Without it every
listing has an empty location and regions.classify_region() buckets it as
"UK-wide / field-national", so overseas roles would show as UK. Location is
therefore rebuilt as a plain string: locality, region, country, falling back to
the "Location: X" line that opens most descriptions.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regions import classify_region_by_name  # noqa: E402

_UK_WORDS = re.compile(r"\b(united kingdom|england|scotland|wales|northern ireland|uk|gb|great britain)\b", re.I)

_LD = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)


def _location(p: dict) -> str:
    loc = p.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    addr = loc.get("address") if isinstance(loc, dict) else None
    if isinstance(addr, list):
        addr = addr[0] if addr else None
    parts = []
    if isinstance(addr, dict):
        for k in ("addressLocality", "addressRegion", "addressCountry"):
            v = addr.get(k)
            if isinstance(v, dict):
                v = v.get("name")
            v = (v or "").strip() if isinstance(v, str) else ""
            if v and v not in parts:
                parts.append(v)
    if not parts:
        desc = re.sub(r"<[^>]+>|&nbsp;", " ", str(p.get("description") or ""))
        m = re.search(r"Location\s*:\s*([^\n\r]{2,80})", desc)
        if m:
            parts.append(m.group(1).strip(" .;"))
    return ", ".join(parts)


def _is_uk(p: dict) -> bool:
    """
    The pipeline has no non-UK gate (regions.classify_region falls back to
    "UK-wide / field-national" for any unrecognised place, e.g. Singapore), and
    Barrington James is a global desk (APAC, US, EU roles). Keep a posting only
    when its location, title or opening description shows a UK signal.
    """
    desc = re.sub(r"<[^>]+>|&nbsp;", " ", str(p.get("description") or ""))[:600]
    text = f"{p.get('jobLocation', '')} {p.get('title', '')} {desc}"
    return bool(_UK_WORDS.search(text) or classify_region_by_name(text))


def parse(html: str, url: str) -> list[dict]:
    out = []
    for block in _LD.findall(html):
        try:
            data = json.loads(block.strip(), strict=False)
        except Exception:
            continue
        for node in data if isinstance(data, list) else [data]:
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                node = dict(node)
                node["jobLocation"] = _location(node)
                if _is_uk(node):
                    out.append(node)
    return out
