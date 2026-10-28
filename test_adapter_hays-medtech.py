"""Run: python3 test_adapter_hays-medtech.py"""
import importlib.util, sys
from pathlib import Path
R = Path(__file__).parent
sys.path.insert(0, str(R / "scripts"))
import crawl_recruiters as c
spec = importlib.util.spec_from_file_location("hm", R / "scripts/adapters/hays-medtech.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
F = R / "fixtures/adapters/hays-medtech"

urls = m.sitemap_urls((F / "job-sitemap-sample.xml").read_text())
assert len(urls) == 5 and all(u.startswith("https://www.hays.co.uk/job-detail/") for u in urls), urls
assert m.slug_title("https://www.hays.co.uk/job-detail/territory-manager---urology--london_4830954") == "territory manager urology london"

def fake_fetch(url, accept="text/html"):
    if url == m.SITEMAP:
        return 200, (F / "job-sitemap-sample.xml").read_text()
    f = F / (url.rsplit("/", 1)[1] + ".html")
    return (200, f.read_text()) if f.exists() else (404, "")

jobs = m.list_jobs(fake_fetch, {})
titles = sorted(j["title"] for j in jobs)
assert titles == ["Territory Manager - Urology", "Tissue Sales Specialist"], titles  # Lancashire (Manufacturing) filtered by industry
n = c.normalise(jobs[0], jobs[0]["url"], "Hays MedTech")
assert n["location_text"] in ("London", "West Midlands"), n["location_text"]
assert n["url"].startswith("https://www.hays.co.uk/job-detail/")
print("hays-medtech adapter: OK")
