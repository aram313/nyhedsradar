"""Sections (Danmark / Mellemøsten / Verden), the ranking lift for Danish politics, channel clean-up and caps."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from radar.feeds import tidy_post  # noqa: E402
from radar.sections import Lexicon, Sections  # noqa: E402

SEC = Sections(json.loads((ROOT / 'config' / 'sections.json').read_text(encoding='utf-8')))


def test_lexicon_word_rules():
    party = Lexicon(['Venstre=', 'EU=', 'gaza', 'غزة'])
    assert party.hits('Venstre styrtdykker i ny måling') == {'venstre'}
    assert not party.hits('Hård kritik af venstrefløjens aktivister')      # the direction, not the party
    assert party.hits("EU's budget") and not party.hits('Europa')
    assert party.hits('Gazas børn') and party.hits('قصف على غزة') and party.hits('بغزة')


def place(title, source='X', lang='da', hint=None):
    item = {'title': title, 'summary': '', 'source': source, 'lang': lang}
    return SEC.place([[{**item, 'sig': SEC.signals(item)}]], np.zeros((1, 384), np.float32), hint or {})[0]


def test_places_stories_in_sections():
    assert place('Regeringen vil stramme reglerne for statsborgerskab')[0] == 'dk'
    assert place('Israel bomber Gaza igen i nat')[0] == 'me'
    assert place('Trump og Putin aftaler diesel-handel')[0] == 'world'
    assert place('Danish mosque attacked in Copenhagen', lang='en')[0] == 'dk'
    # a story without telling words follows its source and language
    assert place('Ny rapport vækker opsigt', source='DR Indland', hint={'DR Indland': 'dk'}) == ['dk']
    assert place('A new report raises eyebrows', lang='en') != ['dk']
    assert place('Mange børn rammes', source='DR Udland', hint={'DR Udland': 'abroad'}) != ['dk']


def test_core_and_light_news_signals():
    s = SEC.signals({'title': 'Muslimsk forsker overfaldet på Aarhus Universitet', 'summary': ''})
    assert s['core_dk'] == 2 and s['named']
    assert SEC.signals({'title': 'Chance for nordlys over hele landet', 'summary': ''})['trivia']
    assert SEC.signals({'title': '17-årig anholdt for drabsforsøg', 'summary': ''})['local']


def test_channel_posts_lose_alarm_tags():
    assert tidy_post('⚡️ Gaza sources Shahd was killed by gunfire') == 'Shahd was killed by gunfire'
    assert tidy_post('Breaking | Israeli forces storm Jenin') == 'Israeli forces storm Jenin'
    assert tidy_post('عاجل | قوات الاحتلال تقتحم') == 'قوات الاحتلال تقتحم'
    assert tidy_post('Israeli sources say the army will withdraw') == 'Israeli sources say the army will withdraw'
    assert tidy_post('»Det går ikke« siger ministeren') == '»Det går ikke« siger ministeren'


def test_danish_politics_is_shown_and_everyday_news_is_not(tmp_path, monkeypatch):
    import importlib
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    from test_run import NoTranslator, make_item
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(
        '\n'.join(json.dumps({'d': '2026-09-01', 't': t}) for t in
                  ['Regeringen strammer reglerne for statsborgerskab', 'Gaza Israel', 'Iran truer Israel']), encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    items = [make_item(1, 'Regeringen vil stramme reglerne for statsborgerskab markant', 'DR Politik')]
    items += [make_item(10 + i, f'Vejret bliver {w} og blæsende i weekenden', 'TV 2 Fyn')
              for i, w in enumerate(['koldt', 'vådt', 'gråt', 'mildt', 'køligt', 'klamt'])]
    items += [make_item(20 + i, f'Mand anholdt efter indbrud i {by} i nat', 'TV 2 Nord')
              for i, by in enumerate(['Aalborg', 'Hjørring', 'Skagen', 'Thisted', 'Brønderslev'])]
    items += [make_item(40 + i, f'Gaza Israel ord{i}a ord{i}b ord{i}c ord{i}d', 'QudsN', lang='en') for i in range(12)]
    monkeypatch.setattr(run, 'fetch_all', lambda f: (items, {}))
    run.main()
    data = json.loads((tmp_path / 'state' / 'data.json').read_text(encoding='utf-8'))
    by_title = {i['title']: i for i in data['items']}
    pol = by_title.get('Regeringen vil stramme reglerne for statsborgerskab markant')
    assert pol and pol['sec'] == 'dk', data['items']
    assert not any(t.startswith(('Vejret', 'Mand anholdt')) for t in by_title), list(by_title)
    # one busy channel fills at most a handful of lines per day
    assert sum(1 for i in data['items'] if i['source'] == 'QudsN') <= 6
    assert all(i['sec'] in ('dk', 'me', 'world') and 'rank' in i for i in data['items'])
    search = json.loads((tmp_path / 'state' / 'search.json').read_text(encoding='utf-8'))
    assert any(x['t'].startswith('Vejret') for x in search['items']), 'search still finds what the lists leave out'
