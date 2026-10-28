"""Run: python3 test_adapter_barrington-james.py  (loads the hyphenated module by path)."""
import importlib.util, json, sys
from pathlib import Path
R = Path(__file__).parent
sys.path.insert(0, str(R / "scripts"))
spec = importlib.util.spec_from_file_location("bj", R / "scripts/adapters/barrington-james.py")
bj = importlib.util.module_from_spec(spec); spec.loader.exec_module(bj)
import crawl_recruiters as c
F = R / "fixtures/adapters/barrington-james"

def load(n): return (F / n).read_text(encoding="utf-8")

def test_invalid_jsonld_is_dropped_by_shared_extractor_but_parsed_by_adapter():
    h = load("account-manager-3430.html")
    assert c.extract_jobpostings(h) == []
    u = "https://www.barringtonjames.com/job/account-manager-3430/"
    p = bj.parse(h.replace("Singapore", "Manchester, England"), u)  # fixture is a Singapore role
    assert len(p) == 1
    l = c.normalise(p[0], u, "Barrington James")
    assert l["title"] == "Account Manager" and l["location_text"].startswith("Manchester")
    assert "pharmaceutical" in l["description"].lower()

def test_overseas_role_is_not_published_as_uk_wide():
    # Singapore account manager: parsed lenient, but excluded as non-UK.
    assert bj.parse(load("account-manager-3430.html"), "u") == []

def test_uk_signal_kept_and_location_filled():
    h = load("account-manager-3430.html").replace("Singapore", "London, England")
    p = bj.parse(h, "u")
    assert len(p) == 1
    assert "London" in c.normalise(p[0], "u", "Barrington James")["location_text"]

if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); print("ok", k)
