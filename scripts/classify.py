"""
Classification rules for the Medical Sales Hub jobs-map pipeline.

Pure keyword/regex matching — no LLM calls, so this runs free and
deterministically inside GitHub Actions on a daily schedule.

Two gates must BOTH pass for a listing to be kept:
  1. TITLE gate  — job title matches a known sales or clinical-support title pattern
  2. SECTOR gate — title, company or description shows a healthcare/medtech signal

This two-gate design exists because broad titles like "Account Manager" or
"Regional Manager" are extremely common outside healthcare. Without the
sector gate the page would fill with software/FMCG/insurance roles.

Speciality tagging matches the Hub's own 43-speciality taxonomy exactly
(names taken from Hub/speciality-template/pages-map.json), so this page's
filter lines up with the Speciality Index and every speciality page.
"""
import re

# ---------------------------------------------------------------------------
# Title gates
# ---------------------------------------------------------------------------

SALES_TITLE_PATTERNS = [
    r"\bterritory\s*(manager|sales|rep(resentative)?|executive|business\s*manager)\b",
    r"\bterritory\s*business\s*manager\b",
    r"\bregional\s*business\s*manager\b",
    r"\bbusiness\s*manager\b",
    r"\baccount\s*manager\b",
    r"\baccount\s*executive\b",
    r"\bkey\s*account\s*manager\b",
    r"\bnational\s*account\s*(manager|executive)\b",
    r"\bbusiness\s*development\s*(manager|executive|exec|lead)\b",
    r"\bnew\s*business\s*(manager|executive|exec|developer)\b",
    r"\bregional\s*(sales\s*)?manager\b",
    r"\barea\s*(sales\s*)?manager\b",
    r"\bmedical\s*sales\s*(rep(resentative)?|executive|manager)\b",
    # Pharma's traditional job titles — distinct from generic "sales rep"
    r"\bmedical\s*rep(resentative)?\b",
    r"\bprofessional\s*medical\s*rep(resentative)?\b",
    r"\bhospital\s*(sales\s*)?(rep(resentative)?|specialist|executive)\b",
    r"\bprimary\s*care\s*(sales\s*)?(rep(resentative)?|executive)\b",
    r"\bspecialist\s*sales\s*(rep(resentative)?|executive|manager)\b",
    r"\bclinical\s*sales\s*specialist\b",
    r"\bsales\s*representative\b",
    r"\bfield\s*sales\b",
    r"\bcommercial\s*manager\b",
    r"\bsales\s*(executive|manager|consultant|specialist)\b",
    r"\bnational\s*sales\s*manager\b",
    r"\bhead\s*of\s*sales\b",
    r"\bsales\s*director\b",
    # Found by the 16/09/2026 coverage audit: real medical-sales roles that the
    # earlier patterns let through the net.
    r"\bmedical\s*sales\s*associate\b",
    r"\bsales\s*associate\b",
    r"\bbusiness\s*development\s*consultant\b",
    r"\bclinical\s*sales\s*support\b",
    r"\bsales\s*support\s*specialist\b",
]

CLINICAL_SUPPORT_TITLE_PATTERNS = [
    r"\bproduct\s*manager\b",
    r"\bproduct\s*specialist\b",
    r"\bclinical\s*lead\b",
    r"\bclinical\s*specialist\b",
    r"\bclinical\s*educator\b",
    r"\bclinical\s*trainer\b",
    r"\bclinical\s*applications?\s*(specialist|engineer)?\b",
    r"\btraining\s*manager\b",
    r"\bnurse\s*advisor\b",
    r"\bclinical\s*nurse\s*advisor\b",
    r"\bapplications?\s*specialist\b",
    r"\bmedical\s*science\s*liaison\b",
    r"\bmsl\b",
    r"\bclinical\s*(support|liaison)\s*(manager|specialist)?\b",
    r"\bvascular\s*access\s*specialist\b",
    r"\btheatre\s*specialist\b",
]

_SALES_RE = re.compile("|".join(SALES_TITLE_PATTERNS), re.IGNORECASE)
_CLINICAL_SUPPORT_RE = re.compile("|".join(CLINICAL_SUPPORT_TITLE_PATTERNS), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Sector gate — must appear in title, company name or description
# ---------------------------------------------------------------------------

SECTOR_KEYWORDS = [
    "medical device", "medical devices", "medtech", "med-tech",
    "pharmaceutical", "pharma", "biotech", "life science", "life sciences",
    "diagnostics", "in vitro diagnostic", "ivd",
    "healthcare", "health care", "clinical", "surgical",
    "nhs", "hospital", "hospitals",
    "vascular", "orthopaedic", "orthopedic", "cardiology",
    "wound care", "tissue viability", "continence", "urology",
    "theatre", "operating theatre", "patient monitoring",
    "capital equipment", "consumables",
]
_SECTOR_RE = re.compile("|".join(re.escape(k) for k in SECTOR_KEYWORDS), re.IGNORECASE)

# Benefits packages mention healthcare without the job being healthcare at all.
# A "Global Sales Executive - Enterprise Logistics" passed the sector gate purely
# because its perks list said "Private healthcare". These phrases are stripped
# before the sector test so a benefit can never qualify a listing.
# "hospital plan"/"hospital cash plan" are in here for the same reason, now
# that bare "hospital" is a sector signal.
BENEFIT_NOISE_RE = re.compile(
    r"private\s+(?:medical|health(?:care)?)(?:\s+(?:insurance|cover|cash\s*plan|scheme))?"
    r"|health(?:care)?\s+(?:insurance|cover|cash\s*plan|scheme|benefit)"
    r"|medical\s+(?:insurance|cover|cash\s*plan)"
    r"|hospital\s+(?:cash\s*)?plan"
    r"|dental\s+(?:insurance|cover|plan)"
    r"|\bbupa\b|\bvitality\b|\baxa\s*health\b|\bsimplyhealth\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Role level — for the "role level" filter
# ---------------------------------------------------------------------------

LEVEL_PATTERNS = [
    ("Director / VP", r"\b(director|vp|vice\s*president|head\s*of)\b"),
    ("National sales manager", r"\bnational\s*sales\s*manager\b"),
    ("Regional / area manager", r"\b(regional|area)\s*(sales\s*|business\s*)?manager\b"),
    ("Key account manager", r"\bkey\s*account\s*manager\b|\bnational\s*account\s*(manager|executive)\b"),
    ("Graduate / entry", r"\bgraduate\b|\btrainee\b|\bentry[\s-]*level\b|\bassociate\b"),
    # territory/clinical rep is the catch-all default for a sales-gate match
]

def classify_level(title: str) -> str:
    for label, pattern in LEVEL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return label
    return "Territory / clinical rep"

# ---------------------------------------------------------------------------
# Speciality — the Hub's own 43 specialities, names exactly as they appear in
# Hub/speciality-template/pages-map.json.
#
# ORDER MATTERS: first match wins, so specific anatomical/speciality terms sit
# above broad catch-alls. "cardiac surgery" must reach Cardiology before the
# generic "surgery" term in Theatres and Surgical, and "interventional
# radiology" must beat plain "radiology".
# ---------------------------------------------------------------------------

SPECIALITY_PATTERNS = [
    ("Vascular Access and IV Therapy",
     r"\bvascular\s*access\b|\bpicc\b|\bmidline\b|\bcentral\s*line\b|\bcannula|\biv\s*therapy\b"
     r"|\binfusion\b|\bvenepuncture\b|\bvascular\s*device"),
    ("Vascular Surgery and Peripheral Arterial Disease",
     r"\bvascular\s*surg|\bperipheral\s*arterial\b|\bendovascular\b|\baneurysm\b|\bvaricose\b|\bpad\b"),
    ("Interventional Radiology", r"\binterventional\s*radiolog"),
    ("Cardiology and Cardiac Surgery",
     r"\bcardiolog|\bcardiac\b|\bcardiothoracic\b|\belectrophysiolog|\bstructural\s*heart\b"
     r"|\btavi\b|\bpacemaker\b|\bcath\s*lab\b|\bcoronary\b"),
    ("Oncology and SACT",
     r"\boncolog|\bchemotherap|\bsact\b|\bcancer\b|\bradiotherap|\bbrachytherap"),
    ("Tissue Viability and Wound Care",
     r"\btissue\s*viability\b|\bwound\s*(care|management)\b|\bpressure\s*ulcer|\bnpwt\b"
     r"|\bnegative\s*pressure\s*wound"),
    ("Continence, Bladder and Bowel",
     r"\bcontinence\b|\bincontinence\b|\bbladder\s*and\s*bowel\b|\burinary\s*catheter"),
    ("Urology", r"\burolog|\bprostate\b|\blithotrips|\bturp\b|\bkidney\s*stone"),
    ("Renal", r"\brenal\b|\bdialysis\b|\bnephrolog|\bhaemodialysis\b|\bperitoneal\s*dialysis\b"),
    ("Orthopaedics and Trauma",
     r"\borthop(a)?edic|\barthroplasty\b|\bhip\s*(and\s*knee\s*)?replacement|\bknee\s*replacement"
     r"|\btrauma\b|\bfracture\b|\bspinal\s*implant"),
    ("Colorectal, GI and Endoscopy",
     r"\bcolorectal\b|\bendoscop|\bgastro|\bcolonoscop|\bstoma\b|\bbowel\s*cancer\b|\bgi\b"),
    ("ENT and Head and Neck",
     r"\bent\b|\botolaryngo|\bhead\s*and\s*neck\b|\brhinolog|\btracheostom"),
    ("Audiology and Hearing", r"\baudiolog|\bhearing\s*aid|\bcochlear\b|\bhearing\b"),
    ("Ophthalmology",
     r"\bophthalm|\bcataract\b|\bretina|\bintraocular\b|\biol\b|\bglaucoma\b|\bvitreo|\beye\s*health\b"),
    ("Dermatology", r"\bdermatolog|\bpsoriasis\b|\beczema\b|\bskin\s*(care|condition)"),
    ("Diabetes and Endocrinology",
     r"\bdiabet|\bendocrin|\binsulin\b|\bglucose\s*monitor|\bcgm\b|\bhba1c\b"),
    ("Respiratory",
     r"\brespiratory\b|\bcopd\b|\basthma\b|\bventilat|\boxygen\s*therapy\b|\bspirometr"
     r"|\bsleep\s*apnoea\b|\bcpap\b|\bniv\b"),
    ("Stroke", r"\bstroke\b|\bthrombectom|\bthrombolys"),
    ("Neurology and Neurosurgery",
     r"\bneurolog|\bneurosurg|\bepilep|\bparkinson|\bdeep\s*brain\b|\bneuromodulation\b|\bshunt\b"),
    ("Sepsis and the Deteriorating Patient",
     r"\bsepsis\b|\bdeteriorating\s*patient\b|\bnews2\b|\bearly\s*warning\s*score"),
    ("Critical Care", r"\bcritical\s*care\b|\bintensive\s*care\b|\bicu\b|\bitu\b|\bhdu\b"),
    ("Emergency and Urgent Care",
     r"\bemergency\s*(department|medicine|care)\b|\ba&e\b|\burgent\s*care\b|\bresus|\bpre[\s-]*hospital\b|\bambulance\b"),
    ("Infection Prevention and Control",
     r"\binfection\s*(prevention|control)\b|\bipc\b|\bsterilis|\bsteriliz|\bantimicrobial\b"
     r"|\bhand\s*hygiene\b|\bhcai\b|\bdecontamination\b"),
    ("Haematology and Patient Blood Management",
     r"\bhaematolog|\bhematolog|\bblood\s*management\b|\btransfusion\b|\banticoagul|\bcoagulation\b"),
    ("Pathology and Laboratory Medicine",
     r"\bpatholog|\blaborator|\bhistolog|\bmicrobiolog|\bblood\s*science|\bcytolog"),
    ("Pharmacy and Medicines",
     r"\bpharmacy\b|\bpharmacist\b|\bmedicines\s*management\b|\baseptic\b|\bdispensing\b"),
    ("Maternity and Neonatal",
     r"\bmaternity\b|\bobstetric|\bneonat|\bmidwif|\blabour\s*ward\b|\bnicu\b"),
    ("Gynaecology and Women's Health",
     r"\bgyn(a)?ecolog|\bwomen'?s\s*health\b|\bhysterect|\bfertility\b|\bmenopause\b"),
    ("Paediatrics", r"\bpaediatric|\bpediatric|\bchild\s*health\b|\bpicu\b"),
    ("Mental Health", r"\bmental\s*health\b|\bpsychiatr|\bcamhs\b"),
    ("Frailty and Older People",
     r"\bfrailty\b|\bolder\s*people\b|\belderly\s*care\b|\bcare\s*home|\bdementia\b|\bfalls\s*prevention\b"),
    ("Palliative and End-of-Life Care",
     r"\bpalliative\b|\bend[\s-]*of[\s-]*life\b|\bhospice\b"),
    ("Pain Management",
     r"\bpain\s*management\b|\bchronic\s*pain\b|\banalgesi|\bnerve\s*block\b"),
    ("Rehabilitation, Prosthetics and Orthotics",
     r"\brehabilitation\b|\bprosthetic|\borthotic|\bwheelchair\b|\bmobility\s*aid"),
    ("Patient Moving and Handling",
     r"\bmoving\s*and\s*handling\b|\bmanual\s*handling\b|\bpatient\s*handling\b|\bhoist\b"
     r"|\bphysiotherap|\boccupational\s*therap"),
    ("Nutrition and Dietetics",
     r"\bnutrition\b|\bdietetic|\bdietitian\b|\benteral\b|\bparenteral\b|\bpeg\s*feed|\btube\s*feeding\b"),
    ("Obesity and Weight Management", r"\bobesity\b|\bbariatric\b|\bweight\s*management\b"),
    ("Primary Care and General Practice",
     r"\bprimary\s*care\b|\bgeneral\s*practice\b|\bgp\s*(surger|practice)|\bpcn\b"),
    ("Digital and Medical IT",
     r"\bdigital\s*health\b|\bhealth\s*(it|informatics)\b|\bepr\b|\belectronic\s*patient\s*record\b"
     r"|\btelehealth\b|\bremote\s*monitoring\b|\bhealthcare\s*software\b"),
    ("Radiology and Imaging",
     r"\bradiolog|\bimaging\b|\bmri\b|\bct\s*scan|\bultrasound\b|\bx[\s-]*ray\b|\bmammograph"),
    ("Theatres and Surgical",
     r"\btheatre\b|\bsurgical\b|\bsurgery\b|\bperioperative\b|\banaesthe|\bsterile\s*services\b"
     r"|\belectrosurg|\benergy\s*device"),
    ("Capital and Estates Watch",
     r"\bcapital\s*equipment\b|\bestates\b|\bebme\b|\bmedical\s*engineering\b"),
]

def classify_speciality(text: str) -> str | None:
    for label, pattern in SPECIALITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None

# ---------------------------------------------------------------------------
# Clinical-experience-required filter.
#
# Only evaluated for clinical/product roles (Lou's call, 16/09/2026): a sales
# advert saying "RGN desirable" is a nice-to-have, whereas on a clinical role
# the registration is the actual entry requirement, and mixing the two made
# the filter mean two different things depending on the row.
# ---------------------------------------------------------------------------

CLINICAL_REQUIRED_PATTERNS = [
    r"\brgn\b", r"\bregistered\s*nurse\b", r"\bnmc\s*pin\b", r"\bnmc\s*registration\b",
    r"\bodp\b", r"\bparamedic\b", r"\bclinical\s*background\s*(is\s*)?(essential|required|desirable)\b",
    r"\bhealthcare\s*professional\b", r"\bnursing\s*qualification\b", r"\bregistered\s*with\s*the\s*nmc\b",
    r"\bhcpc\s*registrat", r"\bradiograph", r"\bphysiotherapist\b",
]
_CLINICAL_REQUIRED_RE = re.compile("|".join(CLINICAL_REQUIRED_PATTERNS), re.IGNORECASE)


def classify_job(title: str, company: str, description: str) -> dict | None:
    """
    Returns a dict of derived fields, or None if the listing fails either gate.
    """
    haystack_sector = BENEFIT_NOISE_RE.sub(" ", f"{title} {company} {description}")
    if not _SECTOR_RE.search(haystack_sector):
        return None

    is_sales = bool(_SALES_RE.search(title))
    is_clinical_support = bool(_CLINICAL_SUPPORT_RE.search(title))

    if not is_sales and not is_clinical_support:
        return None

    # A title matching both (e.g. "Clinical Specialist - Sales") is treated as
    # clinical/product, since that is the more specific of the two.
    category = "clinical_support" if is_clinical_support else "sales"

    return {
        "category": category,
        "level": "Clinical / product" if category == "clinical_support" else classify_level(title),
        "speciality": classify_speciality(f"{title} {description}"),
        "clinical_experience_required": (
            bool(_CLINICAL_REQUIRED_RE.search(description))
            if category == "clinical_support" else False
        ),
    }
