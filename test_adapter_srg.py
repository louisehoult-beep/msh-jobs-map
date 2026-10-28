"""Run: python3 test_adapter_srg.py"""
import importlib.util, sys
from pathlib import Path
R = Path(__file__).parent
sys.path.insert(0, str(R / "scripts"))
import crawl_recruiters as c
spec = importlib.util.spec_from_file_location("srg", R / "scripts/adapters/srg.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
F = R / "fixtures/adapters/srg"

html = (F / "uk-training-manager.html").read_text()
assert c.extract_jobpostings(html) == [], "generic extractor should NOT see the nested posting"
posts = m.parse(html, "https://www.srgtalent.com/jobs/152056-Training-Manager")
assert len(posts) == 1
n = c.normalise(posts[0], "https://www.srgtalent.com/jobs/152056-Training-Manager", "SRG")
assert n["title"] == "Training Manager" and n["company"] == "SRG"
assert n["location_text"] == "Hampshire", n["location_text"]
assert n["posted_date"] and n["description"]
us = m.parse((F / "us-clinical-research.html").read_text(), "x")
assert us == [], "US roles must be dropped"
print("srg adapter: OK")
