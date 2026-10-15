#!/usr/bin/env python3
"""Rebuild the Stay Current list on The Clinical Hub from the official news pages.

None of the NMC, RCN or CQC publish an RSS feed, so this reads their news listing
pages and pulls out the item links. It deliberately keys off URL shape and anchor
text rather than CSS classes, because those change far more often.

RCNi is the fourth source and works differently: rcni.com sits behind Akamai and
403s every non-browser client, so it cannot be scraped from here or from a GitHub
runner. Its items are read out of the RCNi weekly briefing in Lou's Outlook by
tools/rcni_from_outlook.py and merged in from rcni-inbox.json. That means the
three official sources refresh laptop-independently on the Action, and RCNi
refreshes when the weekly Cowork task runs.

Safety rule: if a source yields nothing, the previous items for that source are kept
and the run exits non-zero. A red run is a signal to fix the parser; it must never
leave Lou with a blank or half-empty page.
"""

import json, os, re, sys, datetime
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(HERE), 'data', 'clinical')
DATA = os.path.join(OUT, 'stay-current-data.json')
RCNI = os.path.join(HERE, 'rcni-inbox.json')
PER_SOURCE = 5
UA = 'Mozilla/5.0 (compatible; ClinicalHubBot/1.0; +https://clinicalhub.elevateandthrive.uk)'

SOURCES = [
    {'key': 'nmc', 'label': 'NMC',
     'listing': 'https://www.nmc.org.uk/news/news-and-updates/',
     'item': re.compile(r'^https://www\.nmc\.org\.uk/news/news-and-updates/[a-z0-9][a-z0-9\-]{15,}/$')},
    {'key': 'rcn', 'label': 'RCN',
     'listing': 'https://www.rcn.org.uk/news-and-events/news',
     'item': re.compile(r'^https://www\.rcn\.org\.uk/news-and-events/news/[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'cqc', 'label': 'CQC',
     'listing': 'https://www.cqc.org.uk/news',
     'item': re.compile(r'^https://www\.cqc\.org\.uk/news/(?:releases/)?[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'nice', 'label': 'NICE',
     'listing': 'https://www.nice.org.uk/news/articles',
     'item': re.compile(r'^https://www\.nice\.org\.uk/news/articles/[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'nhsemp', 'label': 'NHS Employers',
     'listing': 'https://www.nhsemployers.org/news',
     'item': re.compile(r'^https://www\.nhsemployers\.org/articles/[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'ciw', 'label': 'CIW',
     'listing': 'https://www.careinspectorate.wales/news',
     'item': re.compile(r'^https://www\.careinspectorate\.wales/[a-z0-9][a-z0-9\-]{19,}$')},
    {'key': 'ihpn', 'label': 'IHPN',
     'listing': 'https://www.ihpn.org.uk/news/',
     'item': re.compile(r'^https://www\.ihpn\.org\.uk/blog/[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'scw', 'label': 'Social Care Wales',
     'listing': 'https://socialcare.wales/news-stories',
     'item': re.compile(r'^https://socialcare\.wales/news-stories/[a-z0-9][a-z0-9\-]{15,}$')},
    {'key': 'rqia', 'label': 'RQIA',
     'listing': 'https://www.rqia.org.uk/category/news/',
     'item': re.compile(r'^https://www\.rqia\.org\.uk/[a-z0-9][a-z0-9\-]{19,}$')},
]
# NISCC (niscc.info/news/) was tried 28/08/2026 and dropped: its URLs are flat
# (no /news/ path segment), so the same item pattern that works for RQIA pulls in
# old archived pages sitting near the top of the listing HTML — a dry run returned
# items dated December 2024 as the "top" result. Left as a periodic check in
# sources-registry.json instead of a live scrape until a better pattern is found.

# GOV.UK Search API sources — structured JSON, no HTML parsing needed. Added 28/08/2026
# as part of the source registry expansion (sources-registry.json). Each entry filters
# gov.uk's own search index to one organisation's news-and-communications output.
GOVUK_API_SOURCES = [
    {'key': 'ukhsa', 'label': 'UKHSA', 'org': 'uk-health-security-agency'},
    {'key': 'dhsc', 'label': 'DHSC', 'org': 'department-of-health-and-social-care'},
]
GOVUK_API = ('https://www.gov.uk/api/search.json?filter_organisations={org}'
             '&filter_content_purpose_supergroup=news_and_communications'
             '&order=-public_timestamp&count={n}')

MONTHS = {m.lower(): i for i, m in enumerate(
    ['January','February','March','April','May','June','July','August','September','October','November','December'], 1)}
SKIP_TITLES = re.compile(r'^(read more|find out more|news|more|latest news|see all|view all)$', re.I)


def fetch(url):
    req = Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
    with urlopen(req, timeout=45) as r:
        raw = r.read()
    for enc in ('utf-8', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace')


def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = (s.replace('&amp;', '&').replace('&nbsp;', ' ')
          .replace('&#39;', "'").replace('&#039;', "'")
          .replace('&rsquo;', "’").replace('&lsquo;', "‘")
          .replace('&quot;', '"').replace('&ndash;', '–').replace('&mdash;', '—'))
    return re.sub(r'\s+', ' ', s).strip()


# Some card-style listings (CIW, Social Care Wales) wrap heading + summary + a
# "DD Month YYYY" byline + category tag all inside one <a>, so strip_tags()
# concatenates the lot into the title. Cut the title at the first such byline —
# harmless on sources that don't have one, since the pattern simply never matches.
DATE_TAIL = re.compile(
    r'\s+\d{1,2}\s+(January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\s+\d{4}\b.*$', re.I)


def clean_title(s):
    return DATE_TAIL.sub('', s).strip()


def absolutise(href, base):
    if href.startswith('//'):
        return 'https:' + href
    if href.startswith('/'):
        return re.match(r'^(https://[^/]+)', base).group(1) + href
    return href


def find_date(html, pos):
    """Look for a date near the anchor. Returns (iso, 'DD Mon') or (None, '')."""
    window = html[max(0, pos - 600): pos + 900]
    m = re.search(r'datetime="(\d{4})-(\d{2})-(\d{2})', window)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b', window)
        if m and m.group(2).lower()[:3] in [k[:3] for k in MONTHS]:
            d, y = int(m.group(1)), int(m.group(3))
            mo = next(v for k, v in MONTHS.items() if k.startswith(m.group(2).lower()[:3]))
        else:
            m = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', window)
            if not m:
                return None, ''
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        dt = datetime.date(y, mo, d)
    except ValueError:
        return None, ''
    if dt > datetime.date.today() + datetime.timedelta(days=2):
        return None, ''
    return dt.isoformat(), dt.strftime('%d %b')


def scrape(source):
    html = fetch(source['listing'])
    out, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*href="([^"#?]+)[^"]*"[^>]*>(.*?)</a>', html, re.S | re.I):
        url = absolutise(m.group(1), source['listing']).rstrip('/')
        probe = url + '/' if source['key'] == 'nmc' else url
        if not source['item'].match(probe):
            continue
        title = clean_title(strip_tags(m.group(2)))
        if len(title) < 20 or SKIP_TITLES.match(title) or probe in seen:
            continue
        seen.add(probe)
        iso, pretty = find_date(html, m.start())
        out.append({'url': probe, 'title': title, 'src': source['key'],
                    'label': source['label'], 'iso': iso, 'date': pretty})
    out.sort(key=lambda i: i['iso'] or '', reverse=True)
    return out[:PER_SOURCE]


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def render(items):
    rows = []
    for it in items:
        rows.append(
            '\n    <a class="item" data-src="%s" href="%s" target="_blank" rel="noopener">'
            '\n      <div class="row1"><span class="date">%s</span><span class="src %s">%s</span></div>'
            '\n      <h3>%s <span class="arrow">&rarr;</span></h3>'
            '\n    </a>\n' % (it['src'], esc(it['url']), esc(it['date'] or ''), it['src'],
                              it['label'], esc(it['title'])))
    return ''.join(rows)


def scrape_govuk_api(source):
    url = GOVUK_API.format(org=source['org'], n=PER_SOURCE)
    raw = fetch(url)
    data = json.loads(raw)
    out = []
    for r in data.get('results', []):
        link = r.get('link', '')
        if not link.startswith('/'):
            continue
        ts = (r.get('public_timestamp') or '')[:10]
        try:
            dt = datetime.date.fromisoformat(ts) if ts else None
        except ValueError:
            dt = None
        out.append({'url': 'https://www.gov.uk' + link, 'title': r.get('title', '').strip(),
                    'src': source['key'], 'label': source['label'],
                    'iso': dt.isoformat() if dt else None,
                    'date': dt.strftime('%d %b') if dt else ''})
    return out[:PER_SOURCE]


def load_rcni():
    """RCNi items staged from Outlook. Absent is normal on an Action run — the
    Action has no mailbox — so it is not treated as a failure here; the previous
    RCNi items are carried instead."""
    if not os.path.exists(RCNI):
        return []
    try:
        return json.load(open(RCNI, encoding='utf-8')).get('items', [])
    except Exception as e:
        print('  RCNi: rcni-inbox.json unreadable (%s)' % e)
        return []


def main():
    previous = {}
    if os.path.exists(DATA):
        try:
            previous = json.load(open(DATA, encoding='utf-8'))
        except Exception:
            previous = {}
    prev_items = previous.get('items', [])

    collected, failed = [], []

    rcni = load_rcni()
    if rcni:
        used = rcni[:PER_SOURCE]
        print('  RCNi: %d item(s) staged from the Outlook briefing, using %d'
              % (len(rcni), len(used)))
        collected += used
    else:
        kept = [i for i in prev_items if i.get('src') == 'rcni']
        print('  RCNi: nothing staged, keeping %d previous item(s)' % len(kept))
        collected += kept

    for s in SOURCES:
        try:
            got = scrape(s)
        except Exception as e:
            print('  %s: FETCH FAILED (%s)' % (s['label'], e))
            got = []
        if got:
            print('  %s: %d items' % (s['label'], len(got)))
            collected += got
        else:
            kept = [i for i in prev_items if i.get('src') == s['key']]
            print('  %s: nothing parsed, keeping %d previous item(s)' % (s['label'], len(kept)))
            failed.append(s['label'])
            collected += kept

    for s in GOVUK_API_SOURCES:
        try:
            got = scrape_govuk_api(s)
        except Exception as e:
            print('  %s: FETCH FAILED (%s)' % (s['label'], e))
            got = []
        if got:
            print('  %s: %d items' % (s['label'], len(got)))
            collected += got
        else:
            kept = [i for i in prev_items if i.get('src') == s['key']]
            print('  %s: nothing parsed, keeping %d previous item(s)' % (s['label'], len(kept)))
            failed.append(s['label'])
            collected += kept

    collected.sort(key=lambda i: i.get('iso') or '', reverse=True)
    # The same story can come back from two sources (e.g. two GOV.UK organisations);
    # keep the first so the page never lists one link twice.
    _seen = set()
    collected = [i for i in collected if not (i.get('url') in _seen or _seen.add(i.get('url')))]
    if not collected:
        print('ERROR: nothing at all to write; leaving the page untouched.')
        return 1

    today = datetime.date.today()
    stamp = today.strftime('%d/%m/%Y')

    json.dump({'refreshed': today.isoformat(), 'items': collected},
              open(DATA, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

    print('Wrote %d items, refreshed %s' % (len(collected), stamp))
    if failed:
        print('::error::No items parsed from: %s. Page kept the previous entries; the parser needs a look.'
              % ', '.join(failed))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
