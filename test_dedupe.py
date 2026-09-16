"""
Dedupe tests.

Pass 1 exists because of a real failure: Reed is queried with 7 keywords and
the same vacancy comes back under several of them — 224 duplicate rows out of
562 on the first live run with a real key. Same source + same source_id is the
same job, full stop.

Run: python3 -m pytest test_dedupe.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from dedupe import dedupe_listings


def job(**kw):
    base = {
        "source": "reed", "source_id": "1", "title": "Territory Manager",
        "company": "Acme Medical", "location_text": "Leeds", "description": "x",
    }
    base.update(kw)
    return base


def test_same_source_id_collapses():
    """The same Reed job returned by several keyword searches is one job."""
    out = dedupe_listings([job(), job(), job()])
    assert len(out) == 1


def test_same_source_id_survives_differing_location_text():
    """This is the case that leaked through before: identical id, drifting text."""
    out = dedupe_listings([
        job(location_text="Leeds"),
        job(location_text="Leeds, West Yorkshire"),
    ])
    assert len(out) == 1


def test_different_source_ids_but_identical_details_collapse():
    """
    Two different Reed ids with the same title, company AND location is a
    re-advertised role, not two vacancies — and on a jobs page two identical
    rows read as a bug. Pass 2 is meant to collapse these.
    """
    out = dedupe_listings([job(source_id="1"), job(source_id="2")])
    assert len(out) == 1


def test_different_source_ids_with_different_locations_are_kept():
    """Genuinely distinct territories must survive."""
    out = dedupe_listings([
        job(source_id="1", location_text="Leeds"),
        job(source_id="2", location_text="Bristol"),
    ])
    assert len(out) == 2


def test_cross_source_duplicate_collapses_and_records_other_source():
    out = dedupe_listings([
        job(source="reed", source_id="1"),
        job(source="adzuna", source_id="99"),
    ])
    assert len(out) == 1
    assert "adzuna" in out[0]["also_sources"] or "reed" in out[0]["also_sources"]


def test_longer_description_wins_across_sources():
    out = dedupe_listings([
        job(source="reed", source_id="1", description="short"),
        job(source="adzuna", source_id="99", description="a much longer description"),
    ])
    assert len(out) == 1
    assert out[0]["description"] == "a much longer description"


def test_listings_without_source_id_are_not_dropped():
    out = dedupe_listings([
        job(source_id=None, title="A"),
        job(source_id=None, title="B"),
    ])
    assert len(out) == 2
