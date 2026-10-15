#!/usr/bin/env python3
"""Turn RCNi newsletter emails into publishable Stay Current items.

Why this exists rather than a scraper: rcni.com sits behind Akamai and returns
403 to every non-browser client, including a GitHub runner. The one place the
headlines are reliably readable is the RCNi weekly briefing that already lands
in Lou's Outlook, so that is what we read.

Input  : _inbox-staging.json, written by the clinical-hub-weekly Cowork task.
         {"fetched": "YYYY-MM-DD",
          "messages": [{"subject":..., "received":"ISO", "bodyHtml":"..."}]}
Output : rcni-inbox.json, merged into the page by refresh_stay_current.py.

Two rules that matter:

1. NEVER publish a newsletter link as-is. Every href in the email is an Adestra
   redirect (rcninews.rcn.org.uk/c/XXXX) keyed to Lou's own subscriber record.
   Publishing one would attribute every reader's click to her and would rot when
   the campaign expires. Each link is resolved to its canonical rcni.com URL and
   the utm_* / check_logged_in query is stripped before anything is written.

2. A link that will not resolve is dropped, not guessed. A half-built rcni.com
   URL that 404s on a nurse's phone is worse than one fewer headline.
"""

import json, os, re, sys, datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(HERE, '_inbox-staging.json')
OUT = os.path.join(HERE, 'rcni-inbox.json')

MAX_ITEMS = 6
# One briefing carries 15+ links. Without a per-issue cap the newest issue fills
# every slot and the page becomes a copy of one email rather than a fortnight's
# nursing news.
MAX_PER_ISSUE = 3
MAX_AGE_DAYS = 21
UA = 'Mozilla/5.0 (compatible; ClinicalHubBot/1.0; +https://clinicalhub.elevateandthrive.uk)'

TRACKER = re.compile(r'^https://rcninews\.rcn\.org\.uk/[ck]/', re.I)
# The editorial pages we want. Advertiser, portfolio and event links are not news.
CANON = re.compile(r'^https://(?:www\.)?rcni\.com/[a-z0-9\-]+/(?:newsroom/)?(?:news|features|opinion)/', re.I)
DROP_QS = re.compile(r'^(utm_|check_logged_in$|TrackingCode$)', re.I)

# Anchor text that tells the reader nothing on its own.
SKIP_TITLE = re.compile(
    r'^(read more|read now|find out more|see my progress|register.*|view this email.*|'
    r'click here|more|latest|explore cpd|subscribe.*)$', re.I)


def clean_url(url):
    """Strip campaign tracking from a resolved URL, keep everything else."""
    p = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not DROP_QS.match(k)]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), ''))


class _NoRedirect(HTTPRedirectHandler):
    """Read the redirect instead of following it.

    Following it is actively wrong here: the hop lands on rcni.com, which Akamai
    403s for non-browser clients, and the 403 arrives with no Location header —
    so every link would silently resolve to nothing. The 302's own Location is
    all we need, and not fetching the article is faster and politer besides.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = build_opener(_NoRedirect)


def resolve(url, cache):
    """Read one Adestra redirect to get the real article. None if it won't resolve."""
    if url in cache:
        return cache[url]
    dest = None
    try:
        req = Request(url, headers={'User-Agent': UA}, method='HEAD')
        resp = _OPENER.open(req, timeout=30)
        dest = resp.headers.get('Location')
    except HTTPError as e:
        # A blocked redirect surfaces here as the 3xx itself, carrying Location.
        dest = e.headers.get('Location') if e.headers else None
    except (URLError, OSError) as e:
        print('    could not resolve %s (%s)' % (url[-12:], e))
    cache[url] = dest
    return dest


def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    for a, b in (('&amp;', '&'), ('&nbsp;', ' '), ('&#39;', "'"), ('&rsquo;', '’'),
                 ('&lsquo;', '‘'), ('&quot;', '"'), ('&ndash;', '–'),
                 ('&mdash;', '—'), ('&#8217;', '’')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def title_from_id(attr):
    """RCNi names each anchor ZONE_1_LINK_1_NEWS_<headline words>. Last resort
    only: the underscores have eaten the original punctuation, so 'If I lose my
    PIN, I lose my home': nurse speaks out comes back without its quotes or
    colon. Accurate, but it reads like a telegram."""
    m = re.match(r'^ZONE_\d+_LINK_\d+_[A-Z]+_(.+)$', attr or '')
    if not m:
        return ''
    return re.sub(r'_+', ' ', m.group(1)).strip()


def title_from_heading(html, pos):
    """For a 'Read more' button, the real headline is the nearest <strong> above
    it, punctuation intact. Preferred over the id-derived version."""
    window = html[max(0, pos - 2600):pos]
    best = ''
    for m in re.finditer(r'<strong>(.*?)</strong>', window, re.S | re.I):
        text = strip_tags(m.group(1))
        # Section labels ("NEWS", "CARDIOVASCULAR") are short and shouty; skip them.
        if len(text) >= 18 and not text.isupper() and not SKIP_TITLE.match(text):
            best = text
    return best


def harvest(msg, cache):
    """Pull (url, title) pairs out of one newsletter."""
    html = msg.get('bodyHtml') or ''
    received = (msg.get('received') or '')[:10]
    found, seen_dest = [], set()

    for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', html, re.S | re.I):
        attrs, inner = m.group(1), m.group(2)
        href = re.search(r'href="([^"]+)"', attrs)
        if not href or not TRACKER.match(href.group(1)):
            continue
        # /k/ is the unsubscribe + preference-centre path. Never touch it.
        if '/k/' in href.group(1):
            continue

        title = strip_tags(inner)
        if not title or SKIP_TITLE.match(title):
            anchor_id = re.search(r'\bid="([^"]+)"', attrs)
            title = (title_from_heading(html, m.start())
                     or title_from_id(anchor_id.group(1) if anchor_id else ''))
        if len(title) < 18 or SKIP_TITLE.match(title):
            continue

        dest = resolve(href.group(1), cache)
        if not dest or not CANON.match(dest):
            continue
        dest = clean_url(dest)
        if dest in seen_dest:
            continue
        seen_dest.add(dest)
        found.append({'url': dest, 'title': title, 'iso': received})
    return found


def main():
    if not os.path.exists(STAGING):
        print('No %s — nothing staged from Outlook this run.' % os.path.basename(STAGING))
        return 1

    staged = json.load(open(STAGING, encoding='utf-8'))
    messages = staged.get('messages', [])
    if not messages:
        print('Staging file has no messages.')
        return 1

    cutoff = (datetime.date.today() - datetime.timedelta(days=MAX_AGE_DAYS)).isoformat()
    cache, items, seen = {}, [], set()

    for msg in messages:
        got = harvest(msg, cache)
        taken = 0
        for it in got:
            if taken >= MAX_PER_ISSUE:
                break
            if it['iso'] and it['iso'] < cutoff:
                continue
            if it['url'] in seen:
                continue
            seen.add(it['url'])
            items.append(it)
            taken += 1
        print('  %s: %d link(s), took %d' %
              ((msg.get('subject') or '?')[:52], len(got), taken))

    if not items:
        print('ERROR: no publishable RCNi links. Leaving rcni-inbox.json untouched '
              'so the page keeps whatever it already had.')
        return 1

    items.sort(key=lambda i: i['iso'] or '', reverse=True)
    items = items[:MAX_ITEMS]
    for it in items:
        it['src'] = 'rcni'
        it['label'] = 'RCNi'
        try:
            it['date'] = datetime.date.fromisoformat(it['iso']).strftime('%d %b')
        except (ValueError, TypeError):
            it['date'] = ''

    json.dump({'written': datetime.date.today().isoformat(), 'items': items},
              open(OUT, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('Wrote %d RCNi item(s) to %s' % (len(items), os.path.basename(OUT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
