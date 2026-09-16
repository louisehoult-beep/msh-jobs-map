"""
Orchestrator for the Medical Sales Hub jobs-map daily pipeline.

fetch (Reed + Adzuna + specialist boards) -> dedupe -> classify (sales /
clinical-support gate, level, speciality, clinical-experience-required) ->
geocode (postcode -> lat/long where present, else region bucket) -> write
data/jobs-data.json.

Run directly for a live build (needs REED_API_KEY / ADZUNA_APP_ID /
ADZUNA_APP_KEY in the environment):

    python3 scripts/build_jobs_data.py

Run against the bundled fixtures instead (no API keys needed — this is how
the pipeline gets exercised in development and in this scaffolding pass):

    python3 scripts/build_jobs_data.py --fixtures
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def load_dotenv() -> None:
    """
    Read keys from a local `.env` (gitignored) so they never have to be
    exported by hand or pasted into a chat. Real environment variables win,
    which is what lets GitHub Actions supply them as repo secrets instead.
    """
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value and key not in os.environ:
            os.environ[key] = value


load_dotenv()

from classify import classify_job
from dedupe import dedupe_listings
from geocode import geocode_postcodes
from regions import classify_region, classify_region_by_name, extract_postcode

ROOT = Path(__file__).parent.parent
DATA_OUT = ROOT / "data" / "jobs-data.json"
FIXTURES_DIR = ROOT / "fixtures"


# A published salary must be a plausible UK annual figure. Sources mix units
# without declaring them: Reed returns some roles hourly (£24.00, £30.77) and
# some as 0, Adzuna returned one at £6,600. Rendering any of those as "£0k" or
# "£24k a year" is simply wrong, and one Reed role came back at £340,000.
# Anything outside this range is moved to salary_raw and NOT published as a
# salary — "not stated" is honest, a wrong number is not.
SALARY_ANNUAL_MIN = 12_000
SALARY_ANNUAL_MAX = 200_000


def sanitise_salary(job: dict) -> dict:
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo is None and hi is None:
        return job
    implausible = [
        v for v in (lo, hi)
        if v is not None and not (SALARY_ANNUAL_MIN <= v <= SALARY_ANNUAL_MAX)
    ]
    if implausible:
        job["salary_raw"] = {"min": lo, "max": hi}
        job["salary_note"] = "not published as annual — outside plausible annual range"
        job["salary_min"] = None
        job["salary_max"] = None
    return job


def _stable_id(job: dict) -> str:
    basis = f"{job.get('title','')}|{job.get('company','')}|{job.get('location_text','')}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def load_fixtures() -> list[dict]:
    listings = []
    for f in sorted(FIXTURES_DIR.glob("sample_*.json")):
        listings.extend(json.loads(f.read_text(encoding="utf-8")))
    return listings


def fetch_all(use_fixtures: bool) -> list[dict]:
    if use_fixtures:
        return load_fixtures()

    from crawl_recruiters import fetch_recruiter_listings
    from fetch_adzuna import fetch_adzuna_listings
    from fetch_reed import fetch_reed_listings

    listings = []

    reed = fetch_reed_listings()
    print(f"[fetch] reed: {len(reed)}")
    listings.extend(reed)

    adzuna = fetch_adzuna_listings()
    print(f"[fetch] adzuna: {len(adzuna)}")
    listings.extend(adzuna)

    print("[fetch] recruiter sites:")
    recruiter, reports = fetch_recruiter_listings()
    print(f"[fetch] recruiter sites total: {len(recruiter)}")
    listings.extend(recruiter)

    (ROOT / "data" / "crawl-report.json").write_text(
        json.dumps(reports, indent=2), encoding="utf-8"
    )
    return listings


def build(use_fixtures: bool = False) -> dict:
    raw_listings = fetch_all(use_fixtures)
    deduped = dedupe_listings(raw_listings)

    classified = []
    for job in deduped:
        result = classify_job(job.get("title", ""), job.get("company", ""), job.get("description", ""))
        if result is None:
            continue
        job = dict(job)
        job.update(result)
        job["id"] = _stable_id(job)
        sanitise_salary(job)
        job["region"] = classify_region(job.get("location_text", ""))
        # Some recruiters (Carrot) leave jobLocation empty but put the
        # territory in the title — "Key Account Manager - East of England".
        # Only consulted when the location field itself yields nothing.
        if job["region"] == "UK-wide / field-national":
            from_title = classify_region_by_name(job.get("title", ""))
            if from_title:
                job["region"] = from_title
        job["postcode"] = extract_postcode(job.get("location_text", ""))
        classified.append(job)

    postcodes = [j["postcode"] for j in classified if j.get("postcode")]
    coords = geocode_postcodes(postcodes) if postcodes else {}
    for job in classified:
        pc = job.get("postcode")
        latlon = coords.get(pc) if pc else None
        job["lat"], job["lon"] = latlon if latlon else (None, None)

    supplier_hqs: list[dict] = []  # populated once supplier HQ geodata exists — see README

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "fixtures" if use_fixtures else "live",
        "job_count": len(classified),
        "jobs": classified,
        "supplier_hqs": supplier_hqs,
    }
    return output


def main():
    use_fixtures = "--fixtures" in sys.argv
    output = build(use_fixtures=use_fixtures)
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {output['job_count']} jobs to {DATA_OUT} (source={output['source']})")


if __name__ == "__main__":
    main()
