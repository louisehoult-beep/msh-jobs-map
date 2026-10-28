"""Run: python3 test_adapter_cure_talent.py"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))
import crawl_recruiters as c  # noqa: E402

spec = importlib.util.spec_from_file_location("ct", ROOT / "scripts/adapters/cure-talent.py")
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)

html = (ROOT / "fixtures/adapters/cure-talent/job1.html").read_text(encoding="utf-8")
url = "https://www.curetalent.co.uk/careers/28374/Business-Development-Executive-Sme-London-Ct2033"

assert c.extract_jobpostings(html) == [], "shared extractor unexpectedly works; adapter may be redundant"
posts = ct.parse(html, url)
assert len(posts) == 1
l = c.normalise(posts[0], url, "Cure Talent")
assert l["title"] == "Business Development Executive (SME)", l["title"]
assert l["location_text"] == "High Street, London, London, SW1", l["location_text"]
assert (l["salary_min"], l["salary_max"]) == (45000.0, 55000.0)
assert l["posted_date"].startswith("2026-09-21")
assert "<" not in l["description"] and "&lt;" not in l["description"]
assert ct.parse("<html></html>", url) == []
assert ct.parse('<script type="application/ld+json">// <![CDATA[ not json // ]]></script>', url) == []
print("ok")
