#!/usr/bin/env python3
"""The Clinical Hub's publish gate.

WHY THIS EXISTS
---------------
The Clinical Hub publishes to nurses, and Stay Current is the part that changes
without anyone looking at it: tools/refresh_stay_current.py rewrites
stay-current-data.json on a schedule, and sources-registry.json is the record of
what the Hub claims to watch. Two things can go wrong quietly.

  1. THE REGISTRY DRIFTS FROM WHAT ACTUALLY RUNS. On 28/08/2026 the RCN's news
     listing was being scraped and published on the page with no entry in the
     registry at all, while the registry's own preamble said everything it holds
     had been placed against a panel. A registry that is not the full picture is
     worse than no registry, because it is read as one.

  2. THE PAGE GOES STALE OR HALF-EMPTY WITHOUT SAYING SO. The refresher already
     keeps the previous items when a source yields nothing, which is the right
     call — but a reader cannot tell carried-over items from fresh ones, so
     nothing outside this gate would notice a parser that had been dead for a
     month.

Nothing here fetches anything. It reads the files as published, so it runs in a
second, offline, and can sit in front of a deploy.

Run:  python3 site/tools/clinical_verify.py
Exit: 0 clean (warnings allowed), 1 on any failure.
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(HERE, 'sources-registry.json')
STAY = os.path.join(os.path.dirname(HERE), 'data', 'clinical', 'stay-current-data.json')
REFRESHER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'refresh_stay_current.py')

KINDS = ('listing', 'govuk_api', 'periodic', 'outlook', 'rss')
STATUSES = ('live', 'registered')

# How old Stay Current may get before it is a finding rather than a note. The
# live sources are all daily or weekly, so a fortnight without a successful
# refresh means the refresher has stopped, not that the week was quiet.
STALE_WARN_DAYS = 7
STALE_FAIL_DAYS = 14

fails, warns = [], []


def FAIL(area, msg):
    fails.append((area, msg))


def WARN(area, msg):
    warns.append((area, msg))


def today():
    return datetime.date.today()


def as_date(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def load(path):
    if not os.path.exists(path):
        FAIL('files', '%s is missing. The Hub reads it at runtime, so an absent '
                      'file is a blank panel, not a quiet skip.' % os.path.basename(path))
        return None
    try:
        return json.load(open(path, encoding='utf-8'))
    except ValueError as e:
        FAIL('files', '%s is not valid JSON (%s). The page fetches it directly, so '
                      'this breaks Stay Current in the browser.'
                      % (os.path.basename(path), e))
        return None


# --------------------------------------------------------------------------
# 1. THE REGISTRY — is the record of what the Hub watches whole?
# --------------------------------------------------------------------------
def check_registry(reg):
    if reg is None:
        return {}

    reviewed = as_date(reg.get('_last_reviewed'))
    if not reviewed:
        FAIL('registry', '_last_reviewed is missing or unreadable (%r). The registry '
                         'carries dates and cadences, so it has to say when someone '
                         'last looked at it.' % reg.get('_last_reviewed'))
    elif reviewed > today():
        FAIL('registry', '_last_reviewed is %s, which has not happened yet.' % reviewed)
    elif (today() - reviewed).days > 120:
        WARN('registry', 'the registry was last reviewed on %s, over four months ago. '
                         'Cadences and URLs move.' % reviewed)

    panels = reg.get('panels')
    if not isinstance(panels, list) or not panels:
        FAIL('registry', 'the registry holds no panels.')
        return {}

    seen_ids, seen_panels, by_key = {}, set(), {}
    for panel in panels:
        pid = panel.get('id')
        if not pid or not panel.get('label'):
            FAIL('registry', 'a panel is missing its id or label (%r).' % (panel.get('id'),))
            continue
        if pid in seen_panels:
            FAIL('registry', 'panel id %r appears twice.' % pid)
        seen_panels.add(pid)

        sources = panel.get('sources') or []
        if not sources:
            FAIL('registry', 'panel %r holds no sources. An empty panel on the page '
                             'states that nothing is watched there, which is not what '
                             'an unfinished panel means.' % pid)

        for src in sources:
            sid = src.get('id')
            label = '%s/%s' % (pid, sid or '?')
            for field in ('id', 'name', 'kind', 'cadence', 'url', 'status'):
                if not src.get(field):
                    FAIL('registry', '%s carries no %s.' % (label, field))
            if sid in seen_ids:
                FAIL('registry', 'source id %r is used twice (%s and %s). The id is how '
                                 'a source is referred to, so it has to mean one thing.'
                                 % (sid, seen_ids[sid], label))
            elif sid:
                seen_ids[sid] = label

            if src.get('kind') not in KINDS:
                FAIL('registry', '%s carries kind=%r, not one of %s.'
                                 % (label, src.get('kind'), ', '.join(KINDS)))
            if src.get('status') not in STATUSES:
                FAIL('registry', '%s carries status=%r, not one of %s.'
                                 % (label, src.get('status'), ', '.join(STATUSES)))

            url = str(src.get('url') or '')
            if not url.startswith('https://'):
                FAIL('registry', '%s carries url=%r. Every source is one click from the '
                                 'registry, and it has to be a real https link.'
                                 % (label, src.get('url')))

            # ---- INVARIANT: a live source names the scraper that feeds it.
            # 'live' is a claim that something actually refreshes this. Without a
            # scraperKey nothing can check that claim, which is how the RCN
            # listing ran for weeks with no registry entry at all.
            if src.get('status') == 'live':
                key = src.get('scraperKey')
                if not key:
                    FAIL('registry', '%s is marked live but names no scraperKey. "live" '
                                     'is a claim that something refreshes it; a claim '
                                     'nothing can check is not one.' % label)
                else:
                    by_key.setdefault(key, []).append((label, url))
            elif src.get('scraperKey'):
                FAIL('registry', '%s carries a scraperKey but is only "registered". A '
                                 'source that something scrapes is live.' % label)

    # ---- Two entries may share a URL only if they share the scraper too. NHS
    # Employers is deliberately cross-listed under Pay & Conditions and Workforce
    # & Policy, with one scraper behind both; two DIFFERENT scrapers on one URL
    # would mean the same page is being read twice.
    urls = {}
    for panel in panels:
        for src in panel.get('sources') or []:
            urls.setdefault(str(src.get('url') or ''), []).append(src)
    for url, group in urls.items():
        if len(group) < 2:
            continue
        live_keys = {s.get('scraperKey') for s in group if s.get('status') == 'live'}
        if len(live_keys) > 1:
            FAIL('registry', '%s is registered %d times under different scrapers (%s). '
                             'One page read twice is one source, not two.'
                             % (url, len(group), ', '.join(sorted(str(k) for k in live_keys))))
        elif not any(s.get('note') for s in group):
            WARN('registry', '%s is registered %d times (%s) with no note saying why. A '
                             'deliberate cross-listing should say it is one.'
                             % (url, len(group), ', '.join(s.get('id', '?') for s in group)))

    return by_key


# --------------------------------------------------------------------------
# 2. THE REGISTRY AGAINST THE REFRESHER — do they describe the same thing?
# --------------------------------------------------------------------------
def scraper_keys():
    """The keys tools/refresh_stay_current.py actually implements, read out of
    the script rather than restated here, so the two cannot drift apart."""
    if not os.path.exists(REFRESHER):
        FAIL('files', 'tools/refresh_stay_current.py is missing — nothing refreshes '
                      'Stay Current.')
        return set()
    src = open(REFRESHER, encoding='utf-8').read()
    keys = set(re.findall(r"\{'key':\s*'([a-z0-9_]+)'", src))
    # RCNi is merged in from the Outlook staging file rather than declared in a
    # SOURCES list, so it is read from the constant that names it.
    if "RCNI = " in src or 'rcni-inbox.json' in src:
        keys.add('rcni')
    if 'mail-news.json' in src:
        keys.add('mail')
    return keys


def check_registry_matches_refresher(by_key):
    keys = scraper_keys()
    if not keys:
        return
    for key in sorted(keys - set(by_key)):
        FAIL('registry', 'tools/refresh_stay_current.py scrapes %r and publishes it on '
                         'Stay Current, but no registry source claims it. The registry '
                         'says it holds everything the Hub watches, so a reader takes '
                         'its absence as "not watched".' % key)
    for key in sorted(set(by_key) - keys):
        FAIL('registry', 'registry source(s) %s name scraperKey %r, which '
                         'tools/refresh_stay_current.py does not implement. That entry '
                         'is marked live and nothing refreshes it.'
                         % (', '.join(l for l, _ in by_key[key]), key))


# --------------------------------------------------------------------------
# 3. STAY CURRENT — is what is published on the page fit to be there?
# --------------------------------------------------------------------------
def check_stay_current(stay, by_key):
    if stay is None:
        return

    refreshed = as_date(stay.get('refreshed'))
    if not refreshed:
        FAIL('stay-current', 'refreshed is missing or unreadable (%r). The page shows '
                             'this date to the reader.' % stay.get('refreshed'))
    elif refreshed > today():
        FAIL('stay-current', 'refreshed is %s, which has not happened yet.' % refreshed)
    else:
        age = (today() - refreshed).days
        if age > STALE_FAIL_DAYS:
            FAIL('stay-current', 'last refreshed %s, %d days ago. Every live source is '
                                 'daily or weekly, so this is a refresher that has '
                                 'stopped, not a quiet fortnight.' % (refreshed, age))
        elif age > STALE_WARN_DAYS:
            WARN('stay-current', 'last refreshed %s, %d days ago.' % (refreshed, age))

    items = stay.get('items')
    if not isinstance(items, list) or not items:
        FAIL('stay-current', 'no items. A blank Stay Current is a broken page, not an '
                             'empty state.')
        return

    seen = set()
    per_src = {}
    for i, item in enumerate(items):
        label = 'item %d (%s)' % (i + 1, str(item.get('title') or '')[:48] or 'untitled')
        for field in ('url', 'title', 'src', 'label'):
            if not item.get(field):
                FAIL('stay-current', '%s carries no %s.' % (label, field))

        url = str(item.get('url') or '')
        if not url.startswith('https://'):
            FAIL('stay-current', '%s links to %r, which is not an https URL.'
                                 % (label, item.get('url')))
        elif url in seen:
            FAIL('stay-current', '%s is the same link as an earlier item. The same story '
                                 'twice reads as two.' % label)
        else:
            seen.add(url)

        title = str(item.get('title') or '')
        if title and len(title) < 20:
            WARN('stay-current', '%s has a %d-character title — check the parser has not '
                                 'picked up a "read more" link.' % (label, len(title)))

        d = as_date(item.get('iso'))
        if item.get('iso') and not d:
            FAIL('stay-current', '%s carries iso=%r, which is not a date.'
                                 % (label, item.get('iso')))
        elif d and d > today() + datetime.timedelta(days=2):
            FAIL('stay-current', '%s is dated %s, which has not happened yet.' % (label, d))

        src = item.get('src')
        per_src.setdefault(src, []).append(d)

    # ---- INVARIANT: every item on the page comes from a source the registry
    # admits to watching, and every live source is actually putting items there.
    for src in sorted(k for k in per_src if k):
        if src not in by_key:
            FAIL('stay-current', '%d item(s) are published under src=%r, which no live '
                                 'registry source claims. The page is showing something '
                                 'the Hub does not say it watches.'
                                 % (len(per_src[src]), src))
    for key in sorted(by_key):
        if key == 'mail' and key not in per_src:
            continue  # optional: a week with nothing verified from the mail folders is normal
        if key not in per_src:
            FAIL('stay-current', 'registry source(s) %s are marked live under scraperKey '
                                 '%r, but nothing from them is on the page. The refresher '
                                 'keeps previous items when a source yields nothing, so a '
                                 'source that has fallen out entirely has been failing for '
                                 'a while.'
                                 % (', '.join(l for l, _ in by_key[key]), key))
            continue
        dates = [d for d in per_src[key] if d]
        if dates and refreshed and (refreshed - max(dates)).days > 60:
            WARN('stay-current', '%r has published nothing since %s. Either that source '
                                 'has gone quiet or its parser has stopped matching.'
                                 % (key, max(dates)))


def main():
    reg = load(REGISTRY)
    stay = load(STAY)
    by_key = check_registry(reg)
    check_registry_matches_refresher(by_key)
    check_stay_current(stay, by_key)

    for area, msg in warns:
        print('WARN  [%s] %s' % (area, msg))
    for area, msg in fails:
        print('FAIL  [%s] %s' % (area, msg))

    if fails:
        print('\nCLINICAL VERIFY FAILED — %d failure(s), %d warning(s).'
              % (len(fails), len(warns)))
        return 1
    print('\nCLINICAL VERIFY PASSED — %d warning(s).' % len(warns))
    return 0


if __name__ == '__main__':
    sys.exit(main())
