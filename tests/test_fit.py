"""The sources' fit and the editor's level in a whole radar run: which outlet leads a story, what Live admits, and the
slim app.json beside the full data.json."""
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run import SHARED, NoTranslator, make_item  # noqa: E402


def _setup(tmp_path, monkeypatch, **settings):
    import importlib
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    shutil.copytree(Path(run.ROOT) / 'config', tmp_path / 'config')
    st = json.loads((tmp_path / 'config' / 'settings.json').read_text(encoding='utf-8'))
    (tmp_path / 'config' / 'settings.json').write_text(json.dumps({**st, **settings}), encoding='utf-8')
    monkeypatch.setattr(run, 'CONFIG', tmp_path / 'config')
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    monkeypatch.setenv('RADAR_LIVE', str(tmp_path / 'live.json'))
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(
        '\n'.join(json.dumps({'d': SHARED, 't': t}) for t in
                  ['Israel bomber Gaza igen', 'Regeringen strammer reglerne', 'Iran truer Israel']), encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    return run


WORDS = ('harbour school bridge road park train coach church square field forest beach river tower market valley '
         'island canal mill farm castle garden lake hill desert border coast port airport station').split()


def title(i):
    """A headline of its own (no two share more than the first word), so every one is a story of its own."""
    return f'Iran {WORDS[i]} {WORDS[(i + 7) % 30]}s {WORDS[(i + 13) % 30]}ward {WORDS[(i + 19) % 30]}ing'


def read(tmp_path, name):
    return json.loads((tmp_path / 'state' / name).read_text(encoding='utf-8'))


def test_the_most_informative_outlet_leads(tmp_path, monkeypatch):
    run = _setup(tmp_path, monkeypatch, show_percentile=0, rank_floor=-100)
    items = [
        # DR has the best fit (1.1), BT 0.9, Ekstra Bladet 0.8: DR's headline leads …
        make_item(1, 'Israel bomber Gaza igen i nat flere dræbt', 'BT'),
        make_item(2, 'Israel bomber Gaza igen i nat flere dræbt ifølge', 'DR'),
        make_item(3, 'Israel bomber Gaza igen i nat flere dræbt melder', 'Ekstra Bladet'),
        # … but a curiosity headline never leads a story another outlet tells plainly, whatever its fit
        make_item(10, 'Derfor strammer regeringen reglerne for statsborgerskab igen', 'DR'),
        make_item(11, 'Regeringen strammer reglerne for statsborgerskab igen', 'BT'),
    ]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (items, {}))
    run.main()
    data = read(tmp_path, 'data.json')
    gaza = next(i for i in data['items'] if 'Gaza' in i['title'])
    assert gaza['source'] == 'DR' and gaza['outlets'] == 3 and gaza['fit'] == 1.1, gaza
    rules = next(i for i in data['items'] if 'statsborgerskab' in i['title'])
    assert rules['source'] == 'BT' and rules['title'].startswith('Regeringen'), rules


def test_the_level_admits_and_app_json_is_slim(tmp_path, monkeypatch):
    run = _setup(tmp_path, monkeypatch, show_percentile=0, rank_floor=-100,
                 live_levels={'få': [-100, 3], 'normal': [-100, 5], 'mange': [-100, 8]})
    items = [make_item(i, title(i), 'Al Jazeera', lang='en') for i in range(12)]
    items.append(make_item(50, 'Regeringen vil forbyde tørklæde for muslimske piger i skolen', 'DR'))
    monkeypatch.setattr(run, 'fetch_all', lambda f: (items, {}))
    run.main()
    data, app = read(tmp_path, 'data.json'), read(tmp_path, 'app.json')
    live = data['live']
    assert live['level'] == 'normal' and live['why'] == 'ingen live.json'
    on = [i for i in data['items'] if i['live']]
    assert len(on) == 6 and live['n_24h'] == 6, [(i['title'], i['live'], i['rank']) for i in data['items']]
    hijab = next(i for i in data['items'] if 'tørklæde' in i['title'])
    assert hijab['live'] in ('dk', 'rank')   # Danish politics on Islam and Muslims is never cut
    assert {i['id'] for i in app['items']} == {i['id'] for i in on}
    assert len(data['items']) == 13
    one = app['items'][0]
    assert 'pct' not in one and 'tier' not in one and 'camps' not in one and one['live']
    assert set(app) >= {'updated', 'sections', 'items', 'sources', 'owner', 'analyses', 'live'}
    assert (tmp_path / 'state' / 'app.json').stat().st_size < (tmp_path / 'state' / 'data.json').stat().st_size

    # the editor sets 'få', takes one story under the line and drops one above it
    below = sorted((i for i in data['items'] if not i['live']), key=lambda i: -i['rank'])[-1]
    top = max((i for i in on if i['live'] == 'rank'), key=lambda i: i['rank'])
    today = run.local_now(run.load(run.CONFIG / 'settings.json', {})).date().isoformat()
    (tmp_path / 'live.json').write_text(json.dumps({'updated': run.NOW.isoformat(), 'days': {today: {
        'level': 'få', 'take': [below['id']], 'drop': [top['id']], 'note': 'en stille dag'}}}), encoding='utf-8')
    (tmp_path / 'state' / 'admitted.json').unlink()   # as if Live had not shown the five before
    monkeypatch.setattr(run, 'fetch_all', lambda f: ([], {}))
    run.main()
    data, app = read(tmp_path, 'data.json'), read(tmp_path, 'app.json')
    by_id = {i['id']: i for i in data['items']}
    assert data['live']['level'] == 'få' and data['live']['note'] == 'en stille dag'
    assert by_id[below['id']]['live'] == 'take' and by_id[top['id']]['live'] is None
    assert below['id'] in {i['id'] for i in app['items']} and top['id'] not in {i['id'] for i in app['items']}
    assert sum(1 for i in data['items'] if i['live'] == 'rank') <= 3


def test_live_never_loses_a_story_it_showed(tmp_path, monkeypatch):
    run = _setup(tmp_path, monkeypatch, show_percentile=0, rank_floor=-100,
                 live_levels={'få': [-100, 1], 'normal': [-100, 2], 'mange': [-100, 4]})
    first = [make_item(i, title(i), 'Al Jazeera', lang='en', hours_ago=3) for i in range(2)]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (first, {}))
    run.main()
    shown = {i['id'] for i in read(tmp_path, 'app.json')['items']}
    assert len(shown) == 2
    later = [make_item(10 + i, title(10 + i), 'Reuters', lang='en') for i in range(3)]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (later, {}))
    run.main()
    app = read(tmp_path, 'app.json')
    assert shown <= {i['id'] for i in app['items']}, 'a story Live showed stays while its rank holds'
    assert json.loads((tmp_path / 'state' / 'admitted.json').read_text(encoding='utf-8'))
