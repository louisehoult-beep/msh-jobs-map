"""
Region-classification tests.

These exist because of a real failure: the first live crawl put all 90 jobs
in "UK-wide / field-national", because recruiter JSON-LD carries region NAMES
("North West", "East Midlands,Derbyshire") and the classifier only understood
postcodes. Every case below is a real location string seen in live data.

Run: python3 -m pytest test_regions.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from regions import classify_region

CASES = [
    # postcodes
    ("EH12, Edinburgh", "Scotland"),
    ("LS1, Leeds", "England — North"),
    ("BT1, Belfast", "Northern Ireland"),
    ("B1, Birmingham", "England — Midlands"),
    # region names as recruiters actually publish them
    ("North West", "England — North"),
    ("South West", "England — South West"),
    ("East Midlands,Derbyshire", "England — Midlands"),
    ("London,South East", "London"),
    ("Yorkshire & Humber", "England — North"),
    ("Central & East", "UK-wide / field-national"),
    # city names
    ("Oxford", "England — South & East"),
    ("Dartford", "England — South & East"),
    ("Cardiff", "Wales"),
    ("Central Belt, Glasgow", "Scotland"),
    # nations, and the ireland/northern-ireland ordering trap
    ("Northern Ireland", "Northern Ireland"),
    ("Dublin", "Ireland (ROI)"),
    ("Republic of Ireland", "Ireland (ROI)"),
    # national / field-based
    ("National - UK", "UK-wide / field-national"),
    ("Field-based, UK-wide", "UK-wide / field-national"),
    ("", "UK-wide / field-national"),
]


def test_all_region_cases():
    failures = []
    for text, expected in CASES:
        got = classify_region(text)
        if got != expected:
            failures.append(f"{text!r} -> {got!r}, expected {expected!r}")
    assert not failures, "region misclassifications:\n  " + "\n  ".join(failures)


def test_northern_ireland_beats_ireland():
    """'Northern Ireland' contains 'Ireland' — ordering must not flip it."""
    assert classify_region("Belfast, Northern Ireland") == "Northern Ireland"


def test_postcode_beats_place_name():
    """An explicit postcode is a stronger signal than a stray place word."""
    assert classify_region("EH12 9XY, covering London accounts") == "Scotland"
