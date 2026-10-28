"""
Cure Talent adapter (www.curetalent.co.uk).

The job pages DO carry a schema.org JobPosting, inside
<script type="application/ld+json"> but wrapped in a JavaScript CDATA comment:

    // <![CDATA[
    [{"@context":..., "@type":"JobPosting", ...}]
    // ]]>

so the shared extract_jobpostings() fails json.loads() and returns nothing. The strings
also contain raw newlines, so parsing uses strict=False.
parse() strips the wrapper and returns the same JobPosting dicts. If the JSON
still cannot be read it returns [] (no guessing from the page text).
"""
import json
import re

_BLOCK = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)


def _strip_wrapper(block: str) -> str:
    block = re.sub(r"^\s*//\s*<!\[CDATA\[", "", block.strip())
    block = re.sub(r"//\s*\]\]>\s*$", "", block.strip())
    return block.strip()


def parse(html: str, url: str) -> list:
    out = []
    for block in _BLOCK.findall(html or ""):
        try:
            parsed = json.loads(_strip_wrapper(block), strict=False)
        except Exception:
            continue
        for node in (parsed if isinstance(parsed, list) else [parsed]):
            if not isinstance(node, dict):
                continue
            t = node.get("@type")
            if "JobPosting" in (t if isinstance(t, list) else [t]):
                out.append(node)
    return out
