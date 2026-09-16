# jobs-map-pipeline

Daily-refreshed data feed for the Medical Sales Hub's **Sales Jobs Map** page
(Career Centre). Crawls UK medical-sales and clinical-support vacancies,
classifies them, and publishes `data/jobs-data.json` for the live Hub page
to fetch directly — same pattern as `msh-compare-data` one level up.

**⚠️ A push to `main` IS a publish.** The Hub page fetches
`data/jobs-data.json` straight from `raw.githubusercontent.com` with no
staging step. `python3 verify.py` must exit 0 before any push — it runs in
CI (`.github/workflows/daily-refresh.yml`) and in `hooks/pre-push`. Install
the hook after cloning:

```bash
git config core.hooksPath hooks
```

## Status (16/09/2026)

**Scaffolded, not yet live.** The pipeline runs end-to-end against bundled
fixtures (proves classify/dedupe/geocode/verify all work) but has never
been pointed at real API keys, never had its keyword lists reviewed by Lou,
and has not been pushed to a GitHub remote or wired into a Hub page yet.
Three things need to happen before this goes live — see "Before going live"
below.

## How it works

```
fetch_reed.py ─┐
fetch_adzuna.py ─┼─► dedupe.py ─► classify.py ─► regions.py ─► geocode.py ─► data/jobs-data.json
fetch_specialist_boards.py ─┘        (title+sector gate,        (postcode → nation/       (postcode →
  (stub — see its docstring)          level, speciality,         territory bucket)          lat/lon via
                                       clinical-experience flag)                              postcodes.io)
```

Orchestrated by `scripts/build_jobs_data.py`.

### Two-gate classification (`scripts/classify.py`)

A listing is only kept if **both** gates pass:

1. **Title gate** — matches a sales title pattern (Territory Manager, Account
   Manager, Business Development, Regional Manager, etc.) OR a clinical-
   support title pattern (Product Manager, Clinical Lead, Nurse Advisor,
   Clinical Educator, etc.)
2. **Sector gate** — company name or description contains a healthcare/
   medtech signal (medical device, pharmaceutical, diagnostics, clinical,
   NHS, surgical, etc.)

The sector gate exists because titles like "Account Manager" or "Regional
Manager" are extremely common outside healthcare — without it the page
would fill with unrelated software/FMCG/insurance roles. See the fixture
`sample_adzuna.json` for two deliberate negative test cases (a SaaS account
manager, an insurance regional manager) that the gate correctly excludes.

Each kept listing is also tagged:
- `category`: `"sales"` or `"clinical_support"` — the two top-level filter
  toggles requested for the page.
- `level`: Territory/clinical rep, Key account manager, Regional/area
  manager, National sales manager, Director/VP, Graduate/entry, or
  Clinical/product.
- `speciality`: matched against the same speciality names as the Hub's
  Speciality Index, where the listing mentions one.
- `clinical_experience_required`: true when the description contains
  clinical-qualification language (RGN, NMC pin, ODP, paramedic, etc.) —
  this is the filter requested for roles that need a clinical background.
- `region`: one of the 10 nation/territory buckets used by the map filter
  (`scripts/regions.py`), derived from any UK postcode area or Eircode
  found in the location text, falling back to "UK-wide / field-national".

### Sources

| Source | Status |
|---|---|
| **Recruiter sites** (`scripts/crawl_recruiters.py` + `recruiters.json`) | **The primary source.** Specialist medical-sales agencies publish `schema.org/JobPosting` JSON-LD on their own job pages — the structured format they publish deliberately so Google for Jobs and other aggregators can index them. Verified working on Zenopa and CHASE 16/09/2026, returning title, structured location, salary min/max, employment type, industry and posted date. |
| Reed API (`scripts/fetch_reed.py`) | Official, free developer key. Needs `REED_API_KEY`. |
| Adzuna API (`scripts/fetch_adzuna.py`) | Official, free tier (1,000 calls/month). Needs `ADZUNA_APP_ID` + `ADZUNA_APP_KEY`. |

### Why recruiter sites rather than LinkedIn

For UK medical sales this route is **more** complete than LinkedIn, not less:
agencies post every vacancy to their own site first and syndicate outwards
afterwards, so the agency site is the primary record. It also yields richer
data than a scraped listing (real salary bands, structured location,
industry classification), and it is the *invited* route — JSON-LD JobPosting
exists precisely so that machines can read it.

**Deliberately not sourced:** Indeed (Publisher API retired 2023, no public
API, direct requests return a Cloudflare 403) and LinkedIn (its User
Agreement §8.2 prohibits automated scraping; the practical risk is account
restriction, and the contractual risk is real). See "LinkedIn" in the
pipeline notes if this is revisited.

### Crawl discipline (built in, not bolted on)

- `robots.txt` is fetched **with our own User-Agent** and honoured per host,
  every run. Note: Python's `RobotFileParser.read()` must not be used for
  this — it fetches with Python's default UA, which several of these sites
  block, and on a 403 it sets `disallow_all`, making a site that genuinely
  permits crawling read as "everything forbidden". We fetch the text
  ourselves and call `.parse()` on it.
- If `robots.txt` cannot be read (403/5xx/network error), the crawler
  **fails closed** and does not crawl that host.
- One request at a time per host, 1.5s apart, identifying User-Agent with a
  contact URL.
- Sitemap `<lastmod>` drives incremental fetching, so a daily run re-fetches
  only what actually changed.
- `MAX_AGE_DAYS` drops postings older than 120 days.

### Adding a recruiter

`scripts/probe_sources.py` checks a domain for robots rules, JSON-LD
JobPosting, RSS feeds and JSON endpoints, and writes `data/source-probe.json`.
Use it to work out the right route, then add an entry to `recruiters.json`
with `job_url_pattern` (and `listing_pages` if the site's job URLs aren't in
its sitemap, as is the case for Zenopa).

### Supplier HQ pins

`data/jobs-data.json` has a `supplier_hqs` field, currently always `[]`.
The Hub's supplier dataset (`../msh-compare-data`'s supplier seed, or
`Hub/company-aliases/company-alias-registry.json`) has **no postcode,
address or lat/long field at all** — this needs a separate one-off
enrichment pass on the supplier data before HQ pins can appear on the map.
Not blocking the jobs layer; the map/filters/page already support toggling
this layer on once the data exists.

## Running locally

Against bundled fixtures (no API keys needed):

```bash
python3 scripts/build_jobs_data.py --fixtures
python3 verify.py
```

Against live sources (needs the env vars below):

```bash
export REED_API_KEY=...
export ADZUNA_APP_ID=...
export ADZUNA_APP_KEY=...
python3 scripts/build_jobs_data.py
python3 verify.py
```

Test the gate itself:

```bash
python3 -m pytest test_verify.py -q
```

## Before going live

1. **Lou registers two free API keys** (I can't create accounts on her
   behalf — standing rule): Reed at reed.co.uk/developers/jobseeker, Adzuna
   at developer.adzuna.com. Both take under 2 minutes, no card needed.
2. **Lou reviews the keyword/title lists** in `scripts/classify.py` — the
   sales and clinical-support title patterns, and the sector-signal list —
   before this runs against real data and reaches members.
3. **Create the GitHub remote, add the two keys as repo secrets**
   (`REED_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`), push, and confirm
   `daily-refresh.yml` runs clean on its first `workflow_dispatch`.
4. **Wire the Hub page** to fetch `https://raw.githubusercontent.com/<owner>/jobs-map-pipeline/main/data/jobs-data.json`
   (same pattern as `hub-calendar-page.html` fetching `msh-compare-data`),
   publish it under page 675 per `HUB-VERIFICATION-STANDARD.md` and the E&T
   CLAUDE.md's Hub-page checklist (parent 675, six PMS ticks, noindex check).
5. Once steps 1–4 are done and confirmed live, record this as a process
   doc in `Process flows for all brands/` per root CLAUDE.md rule 17, and
   run `build-reference-pack.py`.
