"""Run: python3 test_adapter_advance-recruitment.py"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("adv", ROOT / "scripts/adapters/advance-recruitment.py")
adv = importlib.util.module_from_spec(spec); spec.loader.exec_module(adv)
FX = ROOT / "fixtures/adapters/advance-recruitment"
p0, p1 = (FX / "page0.html").read_text(), (FX / "page1.html").read_text()

got0, total, n0 = adv.parse_results(p0)
assert total == 12 and n0 == 8 and len(got0) == 8, (total, n0, len(got0))
j = got0[0]
assert j["title"] == "Inside Sales Executive" and j["jobLocation"] == "Yorkshire"
assert j["url"].startswith("https://www.advancerecruitment.net/careers/")
assert j["baseSalary"]["value"]["minValue"] == 27000 and j["baseSalary"]["value"]["maxValue"] == 30000
ote = [g for g in got0 if "Power Tools" in g["title"]][0]
assert ote["baseSalary"]["value"]["maxValue"] == 39000  # commission after '+' ignored
assert adv._salary("£50,000")["value"]["minValue"] == 50000
assert adv._salary("Competitive") is None

pages = {"https://www.advancerecruitment.net/cm/jobs": p0,
         "https://www.advancerecruitment.net/cm/jobs?page=1": p1}
calls = []
def fetch(url, accept="text/html"):
    calls.append(url)
    return (200, pages[url]) if url in pages else (404, "")
jobs = adv.list_jobs(fetch, {})
# 12 on the site: minus 1 non-UK "International" role, minus 3 duplicate region postings of one vacancy
assert len(jobs) == 8 and len(calls) == 2, (len(jobs), calls)
assert not any(x["jobLocation"].lower() == "international" for x in jobs)
assert sum("Middle East" in x["title"] for x in jobs) == 1
print("ok", len(jobs), "jobs")
