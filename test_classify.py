"""
Classification tests.

The benefits-noise cases are from a real false positive: a "Global Sales
Executive - Enterprise Logistics" role reached the live page because its
perks list said "Private healthcare". A benefit must never qualify a
listing as healthcare.

Run: python3 -m pytest test_classify.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from classify import classify_job

PERKS = ("Package: £70k basic, generous commission, £5,400 car allowance, "
         "Private healthcare, enhanced pension, 23 days plus bank holidays.")


def test_logistics_role_with_healthcare_perk_is_rejected():
    assert classify_job(
        "Global Sales Executive - Enterprise Logistics", "BMS Performance",
        "Selling enterprise logistics and freight-forwarding solutions. " + PERKS,
    ) is None


def test_saas_role_with_medical_insurance_perk_is_rejected():
    assert classify_job(
        "Account Manager", "Generic Software Ltd",
        "SaaS CRM platform for retail clients. Benefits include private medical insurance and dental cover.",
    ) is None


def test_genuine_medical_sales_role_passes_even_with_perks():
    r = classify_job(
        "Territory Manager", "Acme Devices",
        "Selling vascular access medical devices into NHS trusts. " + PERKS,
    )
    assert r is not None and r["category"] == "sales"
    assert r["speciality"] == "Vascular Access and IV Therapy"


def test_sector_signal_in_title_alone_is_enough():
    """'Medical device' in the title should qualify even if the body is thin."""
    r = classify_job("Territory Manager - Medical Devices", "Confidential", "Field sales role.")
    assert r is not None


def test_clinical_support_category_and_clinical_flag():
    r = classify_job(
        "Clinical Nurse Advisor", "Coloplast",
        "Supporting continence and urology product training. RGN registration with the NMC required.",
    )
    assert r["category"] == "clinical_support"
    assert r["clinical_experience_required"] is True


def test_non_healthcare_role_without_any_signal_is_rejected():
    assert classify_job("Regional Manager", "Insurance Brokers Ltd",
                        "Commercial insurance broking across the North West.") is None


def test_hospital_alone_is_a_sector_signal():
    """Added 16/09/2026 — 'hospital' now qualifies a listing on its own."""
    r = classify_job("Territory Business Manager", "Confidential",
                     "Selling into hospital trusts across the North West.")
    assert r is not None


def test_hospital_cash_plan_perk_does_not_qualify():
    """...but a 'hospital cash plan' benefit must not."""
    assert classify_job("Area Sales Manager", "Widgets Ltd",
                        "Selling industrial widgets. Benefits: hospital cash plan, pension.") is None


def test_pharma_medical_representative_title():
    r = classify_job("Medical Representative", "Pharma Co",
                     "Primary care pharmaceutical sales across Yorkshire.")
    assert r is not None and r["category"] == "sales"


def test_regional_and_territory_business_manager_titles():
    for t in ("Regional Business Manager", "Territory Business Manager"):
        r = classify_job(t, "MedTech Ltd", "Selling medical devices into the NHS.")
        assert r is not None, t


def test_clinical_flag_only_set_on_clinical_roles():
    """Lou's rule 16/09/2026: the flag is a clinical-role requirement only."""
    sales = classify_job("Territory Manager", "Acme Devices",
                         "Medical device sales. RGN or registered nurse background desirable.")
    assert sales["category"] == "sales"
    assert sales["clinical_experience_required"] is False

    clin = classify_job("Clinical Nurse Advisor", "Acme Devices",
                        "Wound care product training. RGN with NMC registration required.")
    assert clin["category"] == "clinical_support"
    assert clin["clinical_experience_required"] is True


def test_speciality_names_match_hub_taxonomy():
    cases = [
        ("Territory Manager - Oncology", "Selling SACT and chemotherapy devices", "Oncology and SACT"),
        ("Account Manager", "Respiratory COPD and ventilation portfolio", "Respiratory"),
        ("Sales Specialist", "Ophthalmology cataract and intraocular lens range", "Ophthalmology"),
        ("Product Specialist", "Renal dialysis machines for NHS units", "Renal"),
        ("Territory Manager", "Neurosurgery and epilepsy devices", "Neurology and Neurosurgery"),
        ("Account Manager", "ENT and head and neck surgical range", "ENT and Head and Neck"),
        ("Sales Manager", "Dermatology skin condition treatments", "Dermatology"),
        ("Territory Manager", "Diabetes insulin and CGM glucose monitoring", "Diabetes and Endocrinology"),
    ]
    bad = []
    for title, desc, expected in cases:
        r = classify_job(title, "MedTech Ltd", desc + " medical device NHS")
        got = r["speciality"] if r else None
        if got != expected:
            bad.append(f"{title!r}/{desc[:28]!r} -> {got!r}, expected {expected!r}")
    assert not bad, "speciality mismatches:\n  " + "\n  ".join(bad)


def test_cardiac_surgery_beats_generic_surgery():
    r = classify_job("Territory Manager", "MedTech Ltd",
                     "Cardiac surgery and structural heart devices for NHS theatres.")
    assert r["speciality"] == "Cardiology and Cardiac Surgery"
