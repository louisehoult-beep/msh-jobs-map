"""
UK/Ireland postcode-area -> nation/territory bucket, for the jobs-map filter.

This is a practical bucketing for a regional map UI, not a precise boundary
lookup — postcode areas that straddle two conventional regions are assigned
to whichever region they're most associated with. Good enough for "which
blob on the map does this pin belong to", not for anything that needs exact
administrative geography.

Buckets match the ones used in the jobs-map page filter and SVG map.
"""
import re

LONDON = {"E", "EC", "N", "NW", "SE", "SW", "W", "WC"}

SCOTLAND = {
    "AB", "DD", "DG", "EH", "FK", "G", "HS", "IV", "KA", "KW", "KY",
    "ML", "PA", "PH", "TD", "ZE",
}

NORTHERN_IRELAND = {"BT"}

WALES = {"CF", "LD", "LL", "NP", "SA", "SY"}

ENGLAND_NORTH = {
    "BB", "BD", "BL", "CA", "CH", "DH", "DL", "DN", "FY", "HD", "HG",
    "HU", "HX", "L", "LA", "LS", "M", "NE", "OL", "PR", "S", "SK",
    "SR", "TS", "WA", "WF", "WN", "YO", "WV",
}

ENGLAND_MIDLANDS = {
    "B", "CV", "DE", "DY", "LE", "LN", "NG", "NN", "ST", "TF", "WR", "WS",
}

ENGLAND_SOUTH_WEST = {
    "BA", "BH", "BS", "DT", "EX", "GL", "PL", "SN", "SP", "TA", "TQ", "TR",
}

ENGLAND_SOUTH_EAST = {
    "AL", "BN", "CB", "CM", "CO", "CT", "GU", "HP", "IP", "LU", "ME",
    "MK", "NR", "OX", "PE", "PO", "RG", "RH", "SG", "SL", "SO", "SS", "TN",
}

_ORDERED_BUCKETS = [
    ("London", LONDON),
    ("Scotland", SCOTLAND),
    ("Northern Ireland", NORTHERN_IRELAND),
    ("Wales", WALES),
    ("England — North", ENGLAND_NORTH),
    ("England — Midlands", ENGLAND_MIDLANDS),
    ("England — South West", ENGLAND_SOUTH_WEST),
    ("England — South & East", ENGLAND_SOUTH_EAST),
]

_UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2})\d[A-Z0-9]?\s*\d[A-Z]{2}\b", re.IGNORECASE)
_UK_POSTCODE_AREA_RE = re.compile(r"\b([A-Z]{1,2})\d", re.IGNORECASE)
_EIRCODE_RE = re.compile(r"\b[A-Z]\d{2}\s?[A-Z0-9]{4}\b", re.IGNORECASE)

FIELD_BASED_HINTS = re.compile(
    r"\bfield[\s-]*based\b|\bhome[\s-]*based\b|\bnationwide\b|\buk[\s-]*wide\b|\bremote\b",
    re.IGNORECASE,
)


def extract_postcode(location_text: str) -> str | None:
    m = _UK_POSTCODE_RE.search(location_text or "")
    return m.group(0).upper() if m else None


# ---------------------------------------------------------------------------
# Place-name matching.
#
# Recruiter JSON-LD almost never carries a postcode — it carries a region or
# city name ("North West", "East Midlands,Derbyshire", "South West"). Without
# this table every listing falls through to "UK-wide / field-national" and the
# map is meaningless, which is exactly what happened on the first live run.
#
# Order matters: "northern ireland" must be tested before "ireland", and the
# compass regions before the bare county/city names.
# ---------------------------------------------------------------------------

_PLACE_RULES: list[tuple[str, str]] = [
    ("Northern Ireland", r"northern\s*ireland|\bbelfast\b|\bulster\b|londonderry|\bderry\b|\bantrim\b|\barmagh\b"),
    ("Ireland (ROI)", r"republic\s*of\s*ireland|\bdublin\b|\bcork\b|\bgalway\b|\blimerick\b|\bwaterford\b|\bireland\b"),
    ("Scotland", r"\bscotland\b|\bglasgow\b|\bedinburgh\b|\baberdeen\b|\bdundee\b|\bstirling\b|\binverness\b|"
                 r"central\s*belt|\blothian\b|\bfife\b|strathclyde|ayrshire|lanarkshire|highlands|\bperth\b"),
    ("Wales", r"\bwales\b|\bcardiff\b|\bswansea\b|\bnewport\b|\bwrexham\b|\bbangor\b|glamorgan|gwynedd|\bpowys\b"),
    ("London", r"\blondon\b|greater\s*london"),
    ("England — North", r"north\s*west|north\s*east|\byorkshire\b|\bhumber\b|\bmanchester\b|\bliverpool\b|\bleeds\b|"
                        r"\bsheffield\b|newcastle|\bcumbria\b|lancashire|cheshire|merseyside|\bdurham\b|"
                        r"northumberland|teesside|\bhull\b|\bbradford\b|\bbolton\b|\bpreston\b|tyne|\bwirral\b|"
                        r"\bharrogate\b|\bwarrington\b|\bblackburn\b|\bstockport\b"),
    ("England — Midlands", r"\bmidlands\b|birmingham|nottingham|leicester|\bderby\b|coventry|stoke|wolverhampton|"
                           r"northampton|\blincoln\b|staffordshire|warwickshire|worcester|shropshire|telford|"
                           r"derbyshire|nottinghamshire|leicestershire|\brugby\b|\bdudley\b|\bwalsall\b"),
    ("England — South West", r"south\s*west|\bbristol\b|\bbath\b|\bexeter\b|plymouth|cornwall|\bdevon\b|somerset|"
                             r"\bdorset\b|gloucester|wiltshire|swindon|torquay|\btruro\b|bournemouth|\btaunton\b"),
    ("England — South & East", r"south\s*east|east\s*anglia|east\s*of\s*england|home\s*counties|\bkent\b|\bsurrey\b|\bsussex\b|\bessex\b|"
                               r"hertfordshire|cambridge|\boxford\b|\breading\b|brighton|southampton|portsmouth|"
                               r"norwich|ipswich|milton\s*keynes|\bluton\b|berkshire|hampshire|buckinghamshire|"
                               r"bedfordshire|norfolk|suffolk|\bslough\b|\bwatford\b|\bbasingstoke\b|\bcanterbury\b|"
                               r"\bmaidstone\b|\bcrawley\b|\bdartford\b|\bchelmsford\b"),
]

_PLACE_COMPILED = [(label, re.compile(pat, re.I)) for label, pat in _PLACE_RULES]

_NATIONAL_RE = re.compile(
    r"national|uk[\s-]*wide|\bnationwide\b|all\s*uk|united\s*kingdom|\bgb\b|field[\s-]*based|home[\s-]*based|\bremote\b",
    re.IGNORECASE,
)


def classify_region_by_name(location_text: str) -> str | None:
    """Match a region/city name. Returns None if nothing recognisable."""
    text = location_text or ""
    for label, rx in _PLACE_COMPILED:
        if rx.search(text):
            return label
    return None


def classify_region(location_text: str) -> str:
    """
    Returns one of the nation/territory bucket labels used by the jobs-map
    filter, or "UK-wide / field-national" when no fixed postcode area is
    found (e.g. "field-based, covering the South of England" with no code,
    or a role explicitly advertised as nationwide/remote).
    """
    text = location_text or ""

    # 1. A real postcode is the strongest signal — use it first.
    pc = _UK_POSTCODE_RE.search(text)
    if pc:
        area = re.match(r"([A-Z]{1,2})", pc.group(0).upper())
        if area:
            for label, areas in _ORDERED_BUCKETS:
                if area.group(1) in areas:
                    return label

    if _EIRCODE_RE.search(text):
        return "Ireland (ROI)"

    # 2. Then a region or city name — this is what recruiter JSON-LD
    #    actually carries most of the time.
    by_name = classify_region_by_name(text)
    if by_name:
        return by_name

    # 3. An explicit national/field-based statement.
    if _NATIONAL_RE.search(text):
        return "UK-wide / field-national"

    # 4. A bare postcode *area* prefix ("EH12, Edinburgh" style) as a
    #    last resort before giving up.
    area_match = _UK_POSTCODE_AREA_RE.search(text.upper())
    if area_match:
        area = area_match.group(1).upper()
        for label, areas in _ORDERED_BUCKETS:
            if area in areas:
                return label

    return "UK-wide / field-national"
