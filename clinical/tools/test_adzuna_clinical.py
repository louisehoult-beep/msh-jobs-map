import io, json, os, sys, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
import adzuna_clinical as A

JOB = {'title': ' Senior  Carer ', 'redirect_url': 'http://www.adzuna.co.uk/jobs/land/ad/1',
       'company': {'display_name': 'Oak Care Home'},
       'location': {'display_name': 'Lincoln, Lincolnshire', 'area': ['UK', 'East Midlands', 'Lincolnshire', 'Lincoln']}}


def test_normalise():
    r = A.normalise(JOB)
    assert r['title'] == 'Senior Carer' and r['url'].startswith('https://')
    assert r['source'] == 'Adzuna' and r['employer'] == 'Oak Care Home' and r['town'] == 'Lincoln'
    assert A.normalise({'title': '', 'redirect_url': 'https://x'}) is None
    assert A.normalise({'title': 'x', 'redirect_url': ''}) is None


def test_merge_dedupes_on_title_employer_town():
    have = [{'title': 'Senior Carer', 'employer': 'Oak Care Home', 'town': 'Lincoln'}]
    out, n = A.merge(have, [A.normalise(JOB), {'title': 'HCA', 'employer': 'Pine House', 'town': 'Hull', 'url': 'https://y'}])
    assert n == 1 and len(out) == 2


def test_no_keys_returns_nothing(monkeypatch=None):
    os.environ.pop('ADZUNA_APP_ID', None); os.environ.pop('ADZUNA_APP_KEY', None)
    assert A.fetch() == []


def test_budget_and_stop_on_403():
    os.environ['ADZUNA_APP_ID'] = 'x'; os.environ['ADZUNA_APP_KEY'] = 'y'
    calls = []
    def bad(req, timeout=0):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 403, 'no', {}, None)
    assert A.fetch(bad) == [] and len(calls) == 1
    def ok(req, timeout=0):
        calls.append(2)
        return io.BytesIO(json.dumps({'results': [JOB]}).encode())
    calls.clear()
    out = A.fetch(ok)
    assert len(out) == 1 and len(calls) <= A.MAX_CALLS
    os.environ.pop('ADZUNA_APP_ID'); os.environ.pop('ADZUNA_APP_KEY')
