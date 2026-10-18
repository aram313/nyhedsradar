"""One radar run with the brain: the movement's outlets never confirm a story, the camps' sources added later never
move the scale and fill only a few cards, every kind of media takes its turn in a story, the sharp tiers reach the
editor below the taste bar, and the app gets the method's fields."""
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

SHARED = (date.today() - timedelta(days=38)).isoformat()


class NoTranslator:
    def __init__(self, cache_dir):
        pass

    def __call__(self, texts, lang, to='en'):
        return [f'[{to}] {t}' if t else '' for t in texts]


def item(i, title, source, lang='da', hours_ago=1):
    pub = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {'id': f'm{i:05d}', 'title': title, 'summary': '', 'link': f'https://x.test/{i}', 'source': source,
            'lang': lang, 'published': pub}


def setup(tmp_path, monkeypatch, settings=None, method=None):
    import importlib
    import radar.method
    import radar.run as run
    importlib.reload(run)
    from fake_embed import FakeEmbedder
    cfg = tmp_path / 'config'
    shutil.copytree(Path(run.ROOT) / 'config', cfg)
    if settings:
        st = json.loads((cfg / 'settings.json').read_text(encoding='utf-8'))
        st.update(settings)
        (cfg / 'settings.json').write_text(json.dumps(st), encoding='utf-8')
    if method:
        mt = json.loads((cfg / 'method.json').read_text(encoding='utf-8'))
        mt.update(method)
        (cfg / 'method.json').write_text(json.dumps(mt), encoding='utf-8')
        monkeypatch.setattr(radar.method, 'CONFIG', cfg / 'method.json')
    monkeypatch.setattr(run, 'CONFIG', cfg)
    monkeypatch.setattr(run, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(run, 'CACHE', tmp_path / 'cache')
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'profile.jsonl').write_text(
        '\n'.join(json.dumps({'d': SHARED, 't': t}) for t in ['Israel bomber Gaza igen', 'Iran truer Israel']),
        encoding='utf-8')
    monkeypatch.setattr(run, 'Embedder', FakeEmbedder)
    monkeypatch.setattr(run, 'Translator', NoTranslator)
    monkeypatch.setattr(run.feedback, 'pull', lambda since: ([], since))
    monkeypatch.delenv('RADAR_ANALYSES', raising=False)
    return run


def run_with(run, items):
    run.fetch_all = lambda feeds: (items, {})
    run.main()
    return json.loads((run.STATE / 'data.json').read_text(encoding='utf-8'))


def test_the_movements_outlets_never_confirm_and_every_kind_takes_its_turn(tmp_path, monkeypatch):
    run = setup(tmp_path, monkeypatch)
    title = 'Israel bomber Gaza igen natten over flere dræbte'   # + one word of its own: the same headline twice is one item
    items = [item(n, f'{title} {w}', s, lang) for n, (s, lang, w) in enumerate(
        [('DR', 'da', 'ifølge'), ('TV 2', 'da', 'oplyser'), ('حزب التحرير', 'ar', 'kilder'), ('TASS', 'en', 'melder'),
         ('White House', 'en', 'siger'), ('Köklü Değişim', 'tr', 'skriver')], 1)]
    items += [item(100 + i, f'Vejret bliver koldt{i} i weekenden ifølge prognose', 'DR') for i in range(30)]
    data = run_with(run, items)          # the run ends: no kind of media is left waiting in the turns
    gaza = [i for i in data['items'] if 'Gaza' in i['title']]
    assert len(gaza) == 1, [i['title'] for i in data['items']]
    g = gaza[0]
    assert g['outlets'] == 4 and g['confirmed'] == 4            # DR, TV 2, TASS, White House – never the movement
    assert g['source'] in ('DR', 'TV 2')                       # the established outlets lead, the camps follow
    assert set(g['members']) == {f'm{i:05d}' for i in range(1, 7)}
    assert g['camps'] == {'dk': 2, 'bevægelsen': 2, 'ru': 1, 'us': 1}
    assert {a['group'] for a in g['also']} >= {'east', 'official', 'bevægelsen'}
    assert g['first']['source'] and g['tier'] == 5 and 'israel' in g['actors']


def test_sources_added_for_their_camp_never_move_the_scale(tmp_path, monkeypatch):
    base = [item(i, f'Israel bomber Gaza igen meldes der fra område{i} by{i}', 'DR') for i in range(20)]
    base += [item(100 + i, f'Vejret bliver koldt{i} i weekenden ifølge prognose{i}', 'DR') for i in range(60)]
    base += [item(200 + i, f'Iran truer Israel med svar{i} efter angreb{i} på base{i}', 'Reuters', 'en') for i in range(60)]
    camp = [item(500 + i, f'Siberian grain{i} harvest report{i} region{i} number{i}', 'TASS', 'en') for i in range(120)]
    run = setup(tmp_path / 'a', monkeypatch)
    alone = run_with(run, base)
    pct_alone = {k: (v['pct'], v['gpct']) for k, v in json.loads((run.STATE / 'items.json').read_text(encoding='utf-8')).items()}
    run = setup(tmp_path / 'b', monkeypatch)
    both = run_with(run, base + camp)
    pct_both = {k: (v['pct'], v['gpct']) for k, v in json.loads((run.STATE / 'items.json').read_text(encoding='utf-8')).items()}
    assert all(pct_both[k] == pct_alone[k] for k in pct_alone)                       # taste percentiles unmoved
    shown = lambda d: sorted(i['id'] for i in d['items'] if not i['id'].startswith('m005'))
    assert shown(both) == shown(alone)                                                # and the sections' bars


def test_a_camp_source_fills_only_a_few_cards_a_day(tmp_path, monkeypatch):
    run = setup(tmp_path, monkeypatch, settings={'show_percentile': 0, 'rank_floor': -1000})
    camp = [item(500 + i, f'Iran truer Israel nyt{i} varsel{i} grænse{i} sag{i}', 'TASS', 'en') for i in range(10)]
    data = run_with(run, camp + [item(1, 'Israel bomber Gaza igen i nat', 'DR')])
    assert sum(1 for i in data['items'] if i['source'] == 'TASS') == json.loads(
        (run.CONFIG / 'settings.json').read_text(encoding='utf-8'))['max_added_per_day']


def test_the_sharp_tiers_reach_the_editor_below_the_taste_bar(tmp_path, monkeypatch):
    run = setup(tmp_path, monkeypatch, method={'bypass_floor': -1000, 'bypass_per_day': 2})
    words = ['alfa beta gamma delta', 'epsilon zeta theta iota', 'kappa lambda omikron sigma',
             'tau ypsilon omega psi', 'rho chi phi nu']
    acts = [item(10 + n, f'Trump orders troops {w}', 'Reuters', 'en') for n, w in enumerate(words)]
    filler = [item(100 + i, f'Vejret bliver koldt{i} i weekenden ifølge prognose{i}', 'DR') for i in range(60)]
    gaza = [item(1, 'Israel bomber Gaza igen', 'DR'), item(2, 'Iran truer Israel igen', 'DR')]
    data = run_with(run, acts + filler + gaza)
    bypassed = [i for i in data['items'] if i.get('method')]
    assert len(bypassed) == 2 and all(i['tier'] == 2 and 'Trump' in i['title'] for i in bypassed)
    assert all(i['powers'] == ['usa'] for i in bypassed)
    for i in data['items']:
        assert {'tier', 'tags', 'powers', 'actors', 'members', 'camps', 'first'} <= set(i)


def test_every_outlets_headline_is_weighed_and_a_tier_two_of_them_show_holds():
    # the owner, 18/10 ('se om vi har misset noget'): a story was weighed by its lead's headline alone
    import radar.run as run
    from radar.method import Method
    meth = Method()
    no = lambda src: False
    dr = {'title': 'Egyptens præsident fratræder posten i 2030', 'sec': 'me', 'source': 'DR'}
    coup = [{'title': f'Army ousts the government in a coup, {w} reports', 'sec': 'me', 'source': w}
            for w in ('Reuters', 'AP')]
    assert run.weigh_story(meth, [dr], False, None, no)[0] == 5
    tier, tags, _, n = run.weigh_story(meth, [dr] + coup, False, None, no)
    assert tier == 4 and 4 in tags and n == 2
    # one other headline is not enough; a channel's or an off-scale outlet's headline weighs nothing
    assert run.weigh_story(meth, [dr, coup[0]], False, None, no)[0] == 5
    assert run.weigh_story(meth, [dr] + coup, False, None, lambda src: src == 'AP')[0] == 5
    # Albania's protests: one report's 'radicalizes' does not make them the campaign against the belief
    tirana = [{'title': t, 'source': f's{n}'} for n, t in enumerate([
        'Albanian anti-government protesters clash with police in Tirana',
        "Albania's 'Flamingo Revolution' radicalizes in response to prime minister's 'contempt'",
        'Protests in Albania escalate into violent clashes'])]
    assert run.weigh_story(meth, tirana, False, None, no)[0] == 11
    # a member's plain headline never turns a Danish story's 12 into the rest's 11; light news stays light
    dk = {'title': 'Kommunen lukker svømmehallen i Vejle', 'sec': 'dk', 'source': 'TV 2'}
    assert run.weigh_story(meth, [dk, {'title': 'Swimming pool closes', 'source': 'Reuters'}], False, None, no)[0] == 12
    assert run.weigh_story(meth, [dr] + coup, True, None, no)[0] == 13


def test_a_widely_carried_weighty_story_is_in_live_whatever_the_taste_model_says():
    import radar.run as run
    sharp = {1, 2, 3, 4, 6}
    sisi = {'_ref_out': 12, 'confirmed': 12, 'tier': 5, 'sec': 'me', '_tier_n': 14}
    coup = {'_ref_out': 6, 'confirmed': 6, 'tier': 4, 'sec': 'world', '_tier_n': 3}
    assert run.wide_story(sisi, 4, sharp, False) and run.wide_story(coup, 4, sharp, False)
    assert not run.wide_story({**sisi, 'sec': 'world'}, 4, sharp, False)        # the major issues: the Middle East
    assert not run.wide_story({**sisi, '_ref_out': 3}, 4, sharp, False)          # widely carried: four outlets
    assert not run.wide_story({**sisi, 'tier': 10}, 4, sharp, False)             # weighty by the books
    assert not run.wide_story({**coup, '_tier_n': 1}, 4, sharp, False)          # 'ousted as press secretary'
    assert not run.wide_story({**sisi, 'confirmed': 0}, 4, sharp, False)
    assert not run.wide_story(sisi, 4, sharp, True)                              # never light news
