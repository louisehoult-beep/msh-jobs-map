"""Run: python3 test_adapter_evolve-selection.py"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).parent
FIX = HERE / "fixtures" / "adapters" / "evolve-selection"
sys.path.insert(0, str(HERE / "scripts"))
spec = importlib.util.spec_from_file_location("ev", HERE / "scripts" / "adapters" / "evolve-selection.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
import crawl_recruiters as c  # noqa: E402


def read(n):
    return (FIX / n).read_text(encoding="utf-8")


def test_job_links():
    p1 = ev.job_links(read("listing_page1.html"))
    p2 = ev.job_links(read("listing_page2.html"))
    assert len(p1) == 9 and len(p2) == 4, (len(p1), len(p2))
    assert not set(p1) & set(p2)


def test_parse_detail_and_normalise():
    url = "https://www.evolveselection.com/job-search/9309-graduate-medical-sales-representative-ophthalmology/sales/yorkshire-and-humber/job"
    posts = ev.parse(read("detail_9309.html"), url)
    assert len(posts) == 1
    n = c.normalise(posts[0], url, "Evolve Selection")
    assert n["title"] == "Graduate Medical Sales Representative - Ophthalmology"
    assert "Yorkshire and Humber" in n["location_text"]
    assert n["posted_date"].startswith("2026-10-08") and n["source_id"] == "V90794"
    assert ev.is_uk(posts[0])


def test_is_uk():
    mk = lambda r: {"jobLocation": {"address": {"addressRegion": r}}}
    assert not ev.is_uk(mk("USA, UK"))
    assert not ev.is_uk(mk("Republic Of Ireland, UK"))
    assert ev.is_uk(mk("Northern Ireland, UK,Republic Of Ireland, UK"))
    assert ev.is_uk({"title": "x"})


def test_list_jobs_pagination_and_non_ascii_url():
    detail = read("detail_9309.html")
    seen = []

    def fetch(url, accept="text/html"):
        seen.append(url)
        if "limitstart=9" in url:
            return 200, read("listing_page2.html")
        if "limitstart=18" in url:
            return 200, "<html></html>"
        if "/job-search/" in url:
            return 200, detail
        return 200, read("listing_page1.html")

    out = ev.list_jobs(fetch, {"domain": "www.evolveselection.com", "listing_pages": ["/browse-view/healthcare/medtech/jobs"]})
    assert len(out) == 13 and all(o["url"].startswith("https://") for o in out)
    assert not any(ord(ch) > 127 for u in seen for ch in u), "URLs must be percent-encoded"
    assert any("limitstart=18" in u for u in seen)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
