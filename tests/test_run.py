"""End-to-end test of one radar run with fake feeds and the fake embedder."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))


class NoTranslator:
    """Stand-in for the offline translation models: tests must not download anything."""
    def __init__(self, cache_dir):
        pass

    def __call__(self, texts, lang, to='en'):
        return [f'[{to}] {t}' if t else '' for t in texts]


def make_item(i, title, source, hours_ago=1, link=None, lang='da'):
    pub = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {'id': f'id{i:04d}', 'title': title, 'summary': '', 'link': link or f'https://x.test/{i}',
            'source': source, 'lang': lang, 'published': pub}


def test_run(tmp_path, monkeypatch):
    monkeypatch.setenv('RADAR_STATE', str(tmp_path / 'state'))
    monkeypatch.setenv('RADAR_CACHE', str(tmp_path / 'cache'))
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(
        '\n'.join(json.dumps({'d': '2026-09-01', 't': t}) for t in
                  ['Israel bomber Gaza igen', 'Hizb ut-Tahrir demonstration i København', 'Iran truer Israel']),
        encoding='utf-8')
    import importlib
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    sources = ['DR', 'TV 2', 'BT', 'Politiken', 'Berlingske']
    items = [make_item(i, f'Israel bomber Gaza – nyt angreb i nat version{i}', sources[i % 5]) for i in range(5)]
    items += [make_item(100 + i, f'Fodboldlandsholdet vinder kamp nummer {i}', 'BT') for i in range(40)]
    items += [make_item(200, 'Gammel nyhed om Gaza', 'DR', hours_ago=100)]
    monkeypatch.setattr(run, 'fetch_all', lambda feeds: (items, {s: {'ok': True, 'items': 1, 'error': None} for s in sources}))
    run.main()
    data = json.loads((tmp_path / 'state' / 'data.json').read_text(encoding='utf-8'))
    titles = [i['title'] for i in data['items']]
    assert any('Gaza' in t for t in titles), titles
    assert not any('Gammel' in t for t in titles)
    assert not any('Fodbold' in t for t in titles)
    gaza = [i for i in data['items'] if 'Gaza' in i['title']]
    assert len(gaza) == 1 and gaza[0]['outlets'] == 5 and gaza[0]['big'], gaza
    # a second run must not rescore or duplicate anything
    run.main()
    data2 = json.loads((tmp_path / 'state' / 'data.json').read_text(encoding='utf-8'))
    assert len(data2['items']) == len(data['items'])


def test_notifies_once_per_story_and_learns(tmp_path, monkeypatch):
    import importlib
    import shutil
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    cfg = tmp_path / 'config'
    shutil.copytree(Path(run.ROOT) / 'config', cfg)
    st = json.loads((cfg / 'settings.json').read_text())
    st.update(notify_min_gap_minutes=0, quiet_hours=[0, 0])
    (cfg / 'settings.json').write_text(json.dumps(st))
    feeds = json.loads((cfg / 'feeds.json').read_text(encoding='utf-8'))
    feeds.append({'name': 'Community', 'community': True, 'url': 'x'})
    (cfg / 'feeds.json').write_text(json.dumps(feeds), encoding='utf-8')
    monkeypatch.setattr(run, 'CONFIG', cfg)
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(json.dumps({'d': '2026-09-01', 't': 'Israel bomber Gaza igen'}), encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    sent = []
    monkeypatch.setattr(run.push, 'send', lambda p: sent.append(p) or {'sent': 1})
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    batches = {'items': []}
    monkeypatch.setattr(run, 'fetch_all', lambda f: (batches['items'], {}))

    filler = [make_item(1000 + i, f'Vejret bliver {w} i weekenden ifølge prognose', 'DR')
              for i, w in enumerate(f'koldt{i} varmt{i} blæsende{i}' for i in range(320))]
    batches['items'] = filler
    run.main()                                   # first run: builds the baseline, never notifies
    assert sent == []

    gaza = [make_item(i, f'Israel bomber Gaza flygtningelejr angreb version{i}', s)
            for i, s in enumerate(['TV 2', 'BT', 'Politiken', 'Berlingske', 'Information'])]
    batches['items'] = filler + gaza
    run.main()
    assert len(sent) == 1 and 'Stor historie' in sent[0]['title'], sent

    batches['items'] = filler + gaza + [make_item(50, 'Israel bomber Gaza flygtningelejr angreb version50', 'Community')]
    run.main()
    assert len(sent) == 1, 'the same story must not be notified twice'
    learned = json.loads((tmp_path / 'state' / 'learned.json').read_text(encoding='utf-8'))
    assert {l['why'] for l in learned} >= {'community', 'big'}


def test_noise_trust_balance_and_danish(tmp_path, monkeypatch):
    import importlib
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(
        '\n'.join(json.dumps({'d': '2026-09-01', 't': t}) for t in
                  ['Israel bomber Gaza igen', 'Iran truer Israel', 'Hizb ut-Tahrir demonstration']), encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    items = [
        make_item(1, 'LIVE Seneste nyt om Israel og Gaza i dag', 'DR'),                        # liveblog: noise
        make_item(2, 'Israel bomber Gaza stadion fodbold kamp', 'BT', link='https://bt.dk/sport/x'),  # sport: noise
        make_item(3, 'Iran truer Israel med nyt angreb natten over', 'Stand 4 Palestine'),   # channel only
        make_item(4, 'Hizb ut-Tahrir demonstration samler mange i København', 'TV 2'),
        make_item(5, 'Hizb ut-Tahrir demonstration samler mange mennesker København', 'DR'),
        make_item(6, 'Israel bomber Gaza igen meldes der fra området', 'Al Jazeera', lang='en'),
    ]
    items += [make_item(100 + i, f'Israel bomber Gaza igen ny melding nummer{i} kilde', 'Middle East Monitor')
              for i in range(8)]
    items += [make_item(300 + i, f'Vejrudsigten lover sol {w}', 'DR') for i, w in enumerate(f'ord{i}' for i in range(60))]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (items, {'DR': {'ok': True, 'items': 1, 'error': None},
                                                            'BT': {'ok': False, 'items': 0, 'error': 'x'}}))
    run.main()
    data = json.loads((tmp_path / 'state' / 'data.json').read_text(encoding='utf-8'))
    titles = [i['title'] for i in data['items']]
    assert not any(t.startswith('LIVE') or 'stadion' in t for t in titles), titles
    hizb = [i for i in data['items'] if 'Hizb' in i['title']]
    assert len(hizb) == 1 and hizb[0]['confirmed'] == 2, hizb
    iran = [i for i in data['items'] if 'Iran' in i['title']]
    assert iran and iran[0]['confirmed'] == 0, iran
    memo = [i for i in data['items'] if i['source'] == 'Middle East Monitor' and i['important'] and not i['big']]
    assert len(memo) <= 4, len(memo)
    en = [i for i in data['items'] if i['lang'] == 'en']
    assert all(i.get('title_da', '').startswith('[da]') for i in en), en
    assert data['sources']['BT']['failing_runs'] == 1


def _setup(tmp_path, monkeypatch):
    import importlib
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(json.dumps({'d': '2026-09-01', 't': 'Israel bomber Gaza igen'}), encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    return run


def test_old_copies_of_a_story_do_not_come_back_as_cards(tmp_path, monkeypatch):
    run = _setup(tmp_path, monkeypatch)
    sources = ['DR', 'TV 2', 'BT', 'Politiken', 'Berlingske']
    gaza = [make_item(i, f'Israel bomber Gaza – nyt angreb i nat version{i}', s) for i, s in enumerate(sources)]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (gaza, {}))
    run.main()
    monkeypatch.setattr(run, 'NOW', run.NOW + timedelta(hours=40))   # the story leaves the 36-hour window
    monkeypatch.setattr(run, 'fetch_all', lambda f: ([], {}))
    run.main()
    data = json.loads((tmp_path / 'state' / 'data.json').read_text(encoding='utf-8'))
    assert len([i for i in data['items'] if 'Gaza' in i['title']]) <= 1, [i['title'] for i in data['items']]


def test_clock_skew_and_untrusted_signals(tmp_path, monkeypatch):
    run = _setup(tmp_path, monkeypatch)
    ahead = make_item(1, 'Israel bomber Gaza ifølge israelsk avis med forkert ur', 'Jerusalem Post', hours_ago=-3)
    monkeypatch.setattr(run, 'fetch_all', lambda f: ([ahead], {}))
    taps = [{'kind': 'share', 'id': 'id0001', 'title': 'something else entirely', 'summary': ''},
            {'kind': 'share', 'id': 'nope', 'title': 'Planted text', 'summary': ''}]
    monkeypatch.setattr(run.feedback, 'pull', lambda since: (taps, since))
    run.main()
    items = json.loads((tmp_path / 'state' / 'items.json').read_text(encoding='utf-8'))
    assert 'id0001' in items and items['id0001']['published'] <= run.NOW.isoformat()   # kept, not 'from the future'
    learned = json.loads((tmp_path / 'state' / 'learned.json').read_text(encoding='utf-8'))
    shared = [l for l in learned if l['why'] == 'copied']
    assert [l['id'] for l in shared] == ['id0001'] and 'forkert ur' in shared[0]['t']   # the radar's own text
