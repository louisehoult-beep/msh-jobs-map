"""Care and nursing vacancies from the Adzuna Job Search API, for Live Clinical Roles.

Adds what HealthJobsUK cannot: private care homes, domiciliary care, nursing agencies.
Needs ADZUNA_APP_ID and ADZUNA_APP_KEY (GitHub secrets on msh-jobs-map, set by Lou).
Without them this returns nothing and the feed is NHS-only, which is not a failure.

Budget: Adzuna's paid plan allows 500 calls a day and 5,000 a month. This runs once a
week and stops at MAX_CALLS, so it uses well under 150 a month.

Terms: Adzuna asks for visible attribution ("Jobs by Adzuna") wherever its listings
are shown, so every role carries source 'Adzuna' and the Hub page shows the credit.
Links are Adzuna's own redirect URLs: the page for the advert, never scraped copy.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://api.adzuna.com/v1/api/jobs/gb/search'
CATEGORY = 'healthcare-nursing-jobs'
TERMS = ['registered nurse', 'care assistant', 'support worker', 'care home',
         'healthcare assistant', 'domiciliary care', 'senior carer', 'nursing home']
PAGES = 3
PER_PAGE = 50
MAX_CALLS = 60
MAX_DAYS_OLD = 30
UA = 'Mozilla/5.0 (compatible; ClinicalHubBot/1.0; +https://medsalesintelligencehub.co.uk)'


def _creds():
    i, k = os.environ.get('ADZUNA_APP_ID'), os.environ.get('ADZUNA_APP_KEY')
    return (i, k) if i and k else None


def normalise(job):
    """One Adzuna result -> one role dict in the feed's shape, or None."""
    title = re.sub(r'\s+', ' ', (job.get('title') or '')).strip()
    url = (job.get('redirect_url') or '').replace('http://', 'https://')
    if not title or not url.startswith('https://'):
        return None
    loc = (job.get('location') or {})
    area = [a for a in (loc.get('area') or []) if a and a != 'UK']
    display = (loc.get('display_name') or '').split(',')
    town = (display[0] if display and display[0] else (area[-1] if area else '')).strip()
    county = (area[1] if len(area) > 1 else (display[1].strip() if len(display) > 1 else '')).strip()
    return {'title': title, 'url': url, 'source': 'Adzuna',
            'employer': ((job.get('company') or {}).get('display_name') or '').strip(),
            'town': town, 'county': county}


def _page(term, page, creds, opener=urllib.request.urlopen):
    q = urllib.parse.urlencode({
        'app_id': creds[0], 'app_key': creds[1], 'what': term, 'category': CATEGORY,
        'results_per_page': PER_PAGE, 'max_days_old': MAX_DAYS_OLD,
        'sort_by': 'date', 'content-type': 'application/json'})
    req = urllib.request.Request('%s/%d?%s' % (BASE, page, q), headers={'User-Agent': UA})
    with opener(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8')).get('results', [])


def fetch(opener=urllib.request.urlopen):
    """All care and nursing roles for the weekly feed. Never raises."""
    creds = _creds()
    if not creds:
        print('  Adzuna: no keys set, skipping (feed stays NHS-only).')
        return []
    out, seen, calls = [], set(), 0
    for term in TERMS:
        for page in range(1, PAGES + 1):
            if calls >= MAX_CALLS:
                print('  Adzuna: call budget (%d) reached.' % MAX_CALLS)
                return out
            calls += 1
            try:
                results = _page(term, page, creds, opener)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 429):
                    print('  Adzuna: HTTP %d (keys rejected or plan limit). Stopping; the feed '
                          'keeps its NHS roles.' % e.code)
                    return out
                print('  Adzuna: %r page %d failed (HTTP %d).' % (term, page, e.code))
                break
            except Exception as e:
                print('  Adzuna: %r page %d failed (%s).' % (term, page, e))
                break
            if not results:
                break
            for job in results:
                r = normalise(job)
                if r and r['url'] not in seen:
                    seen.add(r['url'])
                    out.append(r)
    print('  Adzuna: %d role(s) from %d call(s).' % (len(out), calls))
    return out


def _key(r):
    f = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    return (f(r.get('title')), f(r.get('employer'))[:18], f(r.get('town')))


def merge(existing, extra):
    """Add extra roles that are not already listed (same title, employer, town)."""
    have = {_key(r) for r in existing}
    added = []
    for r in extra:
        k = _key(r)
        if k not in have:
            have.add(k)
            added.append(r)
    return existing + added, len(added)
