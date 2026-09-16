"""
Tests that verify.py's gate actually catches what it was built for.
Run: python3 -m pytest test_verify.py -q
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import verify as v


def _base_job(**overrides):
    job = {
        "id": "abc123",
        "title": "Territory Manager - Vascular Access",
        "company": "Fresenius Kabi",
        "location_text": "EH12, Edinburgh",
        "category": "sales",
        "level": "Territory / clinical rep",
        "region": "Scotland",
        "url": "https://www.reed.co.uk/jobs/example",
        "source": "reed",
        "posted_date": "2026-09-12",
        "lat": None,
        "lon": None,
    }
    job.update(overrides)
    return job


def _base_doc(jobs):
    return {
        "generated_at": "2026-09-16T08:00:00Z",
        "source": "live",
        "job_count": len(jobs),
        "jobs": jobs,
        "supplier_hqs": [],
    }


def _reset():
    v.FAILS.clear()
    v.WARNS.clear()


def _run_all(doc):
    _reset()
    for check in v.CHECKS[1:]:
        check(doc)
    return list(v.FAILS)


def test_good_document_passes():
    doc = _base_doc([_base_job()])
    assert _run_all(doc) == []


def test_missing_required_field_fails():
    job = _base_job()
    del job["company"]
    doc = _base_doc([job])
    fails = _run_all(doc)
    assert any("required_fields" in f for f in fails)


def test_bad_category_fails():
    doc = _base_doc([_base_job(category="marketing")])
    fails = _run_all(doc)
    assert any("category_values" in f for f in fails)


def test_bad_region_fails():
    doc = _base_doc([_base_job(region="Mars")])
    fails = _run_all(doc)
    assert any("region_values" in f for f in fails)


def test_non_https_url_fails():
    doc = _base_doc([_base_job(url="http://insecure.example.com/job")])
    fails = _run_all(doc)
    assert any("urls_are_https" in f for f in fails)


def test_duplicate_ids_fail():
    doc = _base_doc([_base_job(id="dupe"), _base_job(id="dupe")])
    doc["job_count"] = 2
    fails = _run_all(doc)
    assert any("no_duplicate_ids" in f for f in fails)


def test_out_of_bounds_coordinates_fail():
    doc = _base_doc([_base_job(lat=40.7128, lon=-74.0060)])  # New York
    fails = _run_all(doc)
    assert any("coordinates_in_bounds" in f for f in fails)


def test_in_bounds_coordinates_pass():
    doc = _base_doc([_base_job(lat=55.9533, lon=-3.1883)])  # Edinburgh
    assert _run_all(doc) == []


def test_placeholder_company_fails():
    doc = _base_doc([_base_job(company="Sample Supplier 1 Ltd")])
    fails = _run_all(doc)
    assert any("no_placeholder_content" in f for f in fails)


def test_job_count_mismatch_fails():
    doc = _base_doc([_base_job()])
    doc["job_count"] = 5
    fails = _run_all(doc)
    assert any("top_level_shape" in f for f in fails)


def test_main_exits_1_when_data_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "DATA_FILE", tmp_path / "does-not-exist.json")
    assert v.main() == 1
