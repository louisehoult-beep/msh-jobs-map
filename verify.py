#!/usr/bin/env python3
"""
Publish gate for the Medical Sales Hub jobs-map pipeline.

Mirrors the msh-compare-data verify.py pattern: this repo's data/jobs-data.json
is fetched directly by the live Hub page (raw.githubusercontent.com, no
staging step), so a push to main IS a publish. This script must exit 0
before any commit lands, in CI and in hooks/pre-push alike.

If the gate and the data disagree, assume the data is wrong — loosening a
check to make a push go through is how a bad publish reaches members.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "jobs-data.json"

# NOTE on location_text (changed 16/09/2026, deliberately, not to make a run pass):
# it is NOT required. Some recruiters publish a genuinely empty jobLocation —
# Carrot Recruitment does — while the vacancy itself is completely sound (real
# title, real salary band, recent date, working URL). `region` is what the map
# actually renders, it is always populated, and it falls back to
# "UK-wide / field-national", which is an honest statement about a listing whose
# location the recruiter never stated. Requiring location_text would silently
# discard real, high-value vacancies. The strict check stays on `region`.
REQUIRED_JOB_FIELDS = [
    "id", "title", "company", "category", "level",
    "region", "url", "source", "posted_date",
]
VALID_CATEGORIES = {"sales", "clinical_support"}
VALID_REGIONS = {
    "London", "Scotland", "Northern Ireland", "Wales",
    "England — North", "England — Midlands",
    "England — South West", "England — South & East",
    "Ireland (ROI)", "UK-wide / field-national",
}

# UK/Ireland rough bounding box, for lat/lon sanity checking
LAT_RANGE = (49.5, 61.0)
LON_RANGE = (-11.0, 2.0)

FAILS: list[str] = []
WARNS: list[str] = []


def FAIL(check: str, msg: str) -> None:
    FAILS.append(f"[{check}] {msg}")


def WARN(check: str, msg: str) -> None:
    WARNS.append(f"[{check}] {msg}")


def check_file_exists(doc) -> None:
    if doc is None:
        FAIL("file_exists", f"{DATA_FILE} is missing or not valid JSON")


def check_top_level_shape(doc) -> None:
    for key in ("generated_at", "source", "job_count", "jobs", "supplier_hqs"):
        if key not in doc:
            FAIL("top_level_shape", f"missing top-level key '{key}'")
    if "jobs" in doc and not isinstance(doc["jobs"], list):
        FAIL("top_level_shape", "'jobs' must be a list")
    if "job_count" in doc and "jobs" in doc:
        if doc["job_count"] != len(doc["jobs"]):
            FAIL("top_level_shape", f"job_count ({doc['job_count']}) != len(jobs) ({len(doc['jobs'])})")


def check_required_fields(doc) -> None:
    for i, job in enumerate(doc.get("jobs", [])):
        for field in REQUIRED_JOB_FIELDS:
            if field not in job or job[field] in (None, ""):
                FAIL("required_fields", f"job[{i}] (id={job.get('id','?')}) missing/empty '{field}'")


def check_category_values(doc) -> None:
    for job in doc.get("jobs", []):
        if job.get("category") not in VALID_CATEGORIES:
            FAIL("category_values", f"job {job.get('id')} has invalid category '{job.get('category')}'")


def check_region_values(doc) -> None:
    for job in doc.get("jobs", []):
        if job.get("region") not in VALID_REGIONS:
            FAIL("region_values", f"job {job.get('id')} has unrecognised region '{job.get('region')}'")


def check_urls_are_https(doc) -> None:
    for job in doc.get("jobs", []):
        url = job.get("url", "")
        if url and not url.startswith("https://"):
            FAIL("urls_are_https", f"job {job.get('id')} has a non-https url: {url}")


def check_no_duplicate_ids(doc) -> None:
    ids = [j.get("id") for j in doc.get("jobs", [])]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        FAIL("no_duplicate_ids", f"duplicate job ids in output: {sorted(dupes)}")


def check_coordinates_in_bounds(doc) -> None:
    for job in doc.get("jobs", []):
        lat, lon = job.get("lat"), job.get("lon")
        if lat is None and lon is None:
            continue
        if lat is None or lon is None:
            FAIL("coordinates_in_bounds", f"job {job.get('id')} has only one of lat/lon set")
            continue
        if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
            FAIL("coordinates_in_bounds", f"job {job.get('id')} lat/lon ({lat},{lon}) outside UK/Ireland bounding box")


def check_salaries_plausible(doc) -> None:
    """
    A published salary must be a believable UK annual figure. Sources mix
    units without declaring them (Reed returns some roles hourly, one at 0,
    one at £340,000; Adzuna returned one at £6,600). build_jobs_data moves
    those to salary_raw — if one reaches the published fields, the pipeline
    has regressed and it would render as "£0k" or "£24k" on a live page.
    """
    for job in doc.get("jobs", []):
        for field in ("salary_min", "salary_max"):
            v = job.get(field)
            if v is None:
                continue
            if not (12_000 <= v <= 200_000):
                FAIL("salaries_plausible",
                     f"job {job.get('id')} has implausible annual {field}={v} "
                     f"({job.get('title','')[:40]!r}) — should have been moved to salary_raw")


def check_reasonable_volume(doc) -> None:
    # Not a hard fail — a genuinely quiet day is possible — but a sudden
    # collapse to zero usually means a source broke, not that the market did.
    count = doc.get("job_count", 0)
    if doc.get("source") == "live" and count == 0:
        WARN("reasonable_volume", "0 jobs in a 'live' build — check the source APIs are actually returning results")


def check_no_placeholder_content(doc) -> None:
    # This gate specifically must never let sample/mockup data reach the
    # published feed once the pipeline is live (root rule 2: never publish
    # invented facts).
    for job in doc.get("jobs", []):
        for field in ("company", "title"):
            val = str(job.get(field, "")).lower()
            if "sample supplier" in val or val.startswith("placeholder"):
                FAIL("no_placeholder_content", f"job {job.get('id')} looks like placeholder/sample data ('{job.get(field)}')")
    if doc.get("source") == "fixtures":
        WARN("no_placeholder_content", "source='fixtures' — this build must never be the one pushed to main")


CHECKS = [
    check_file_exists,
    check_top_level_shape,
    check_required_fields,
    check_category_values,
    check_region_values,
    check_urls_are_https,
    check_no_duplicate_ids,
    check_coordinates_in_bounds,
    check_salaries_plausible,
    check_reasonable_volume,
    check_no_placeholder_content,
]


def main() -> int:
    doc = None
    if DATA_FILE.exists():
        try:
            doc = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            FAIL("file_exists", f"{DATA_FILE} is not valid JSON: {exc}")

    check_file_exists(doc)
    if doc is not None:
        for check in CHECKS[1:]:
            check(doc)

    if WARNS:
        print("WARNINGS:")
        for w in WARNS:
            print(f"  - {w}")

    if FAILS:
        print("FAILURES (publish blocked):")
        for f in FAILS:
            print(f"  - {f}")
        return 1

    print(f"verify.py: PASS ({len(doc.get('jobs', [])) if doc else 0} jobs, {len(WARNS)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
