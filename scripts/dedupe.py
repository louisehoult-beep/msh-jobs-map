"""
Dedupe listings that appear on more than one source (e.g. the same vacancy
posted on both Reed and Adzuna, or syndicated to a specialist board too).

Key: normalised (title, company, location) — good enough for this purpose
without needing fuzzy matching. When two listings collide, the one with the
longer description wins (usually the more complete record); its source list
is extended so the record can show "also listed on Reed, Adzuna".
"""
import re


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def dedupe_listings(listings: list[dict]) -> list[dict]:
    # Pass 1 — exact identity. A single source returns the same job under
    # several keyword searches (Reed's 7 keyword queries produced 224
    # duplicate rows out of 562 on the first live run). Same source + same
    # source_id is definitionally the same vacancy, so collapse it before
    # the fuzzier title/company/location pass runs.
    exact: dict[tuple, dict] = {}
    passthrough: list[dict] = []
    for job in listings:
        sid = job.get("source_id")
        if sid:
            key = (job.get("source"), str(sid))
            if key not in exact:
                exact[key] = job
        else:
            passthrough.append(job)
    listings = list(exact.values()) + passthrough

    # Pass 2 — same vacancy appearing on different sources.
    by_key: dict[tuple, dict] = {}

    for job in listings:
        key = (_norm(job.get("title")), _norm(job.get("company")), _norm(job.get("location_text")))
        existing = by_key.get(key)

        if existing is None:
            job = dict(job)
            job["also_sources"] = []
            by_key[key] = job
            continue

        existing["also_sources"] = list(set(existing["also_sources"] + [job["source"]]))
        if len(job.get("description", "")) > len(existing.get("description", "")):
            keep_sources = [existing["source"]] + existing["also_sources"]
            merged = dict(job)
            merged["also_sources"] = [s for s in keep_sources if s != job["source"]]
            by_key[key] = merged

    return list(by_key.values())
