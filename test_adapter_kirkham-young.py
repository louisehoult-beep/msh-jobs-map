import importlib.util, pathlib
here = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("ky", here / "scripts/adapters/kirkham-young.py")
ky = importlib.util.module_from_spec(spec); spec.loader.exec_module(ky)
html = (here / "fixtures/adapters/kirkham-young/careers.html").read_text()
jobs = ky.parse_listing(html)
assert len(jobs) == 3, len(jobs)
j = jobs[0]
assert j["title"] == "Strategic Healthcare Partnership Manager"
assert j["identifier"] == "SK12812" and j["datePosted"] == "2026-10-28"
assert j["url"].endswith("/careers/#SK12812")
assert "London" in j["jobLocation"] and j["industry"] == "Medical"
assert "NHS" in j["description"] and "<" not in j["description"]
assert jobs[1]["title"] == "Medical Sales – Cardiology", jobs[1]["title"]
assert ky.parse_listing("<html></html>") == []
assert ky.list_jobs(lambda u, accept=None: (503, ""), {}) == []
print("ok")
