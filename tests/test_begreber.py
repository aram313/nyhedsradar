"""The wiki of concepts (public/viden/begreber.json and the linker's begreber-index.json) keeps the shared schema and
Khabar's rules: every text is Hizb ut-Tahrir's reading, attributed and dated, from an answer the movement index holds;
the newest answer governs the lead; an alias names one page and is never an ordinary Danish word, an adjective or a
word for a people; the movement layer's voice rules hold; and the concept pages merge with their own entry winning a
clash."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_begreber as bb  # noqa: E402

VIDEN = ROOT / 'public' / 'viden'
DOC = json.loads((VIDEN / 'begreber.json').read_text(encoding='utf-8'))
INDEX = json.loads((VIDEN / 'begreber-index.json').read_text(encoding='utf-8'))
LAYER = json.loads((VIDEN / 'movement.json').read_text(encoding='utf-8'))
ANSWERS = json.loads((VIDEN / 'movement-index.json').read_text(encoding='utf-8'))['answers']
ITEMS = DOC['items']
FIELDS = {'id', 'name', 'kind', 'aliases', 'case_sensitive', 'lead_da', 'lead_nr', 'lead_date', 'timeline', 'relations',
          'answers', 'related'}
needs_seed = pytest.mark.skipif(not bb.SEED.exists(), reason='docs/hjerne/knowledge-v0.json is not here')


def texts(e):
    yield 'lead', e['lead_da']
    for i, r in enumerate(e['timeline']):
        yield f'timeline[{i}]', r['text_da']
    for i, r in enumerate(e['relations']):
        yield f'relation[{i}]', r['text_da']


def page(**over):
    p = {'id': 'testland', 'name': 'Testland', 'kind': 'stat', 'aliases': ['Testland'], 'case_sensitive': True,
         'lead_da': 'Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er Testland en stat.', 'lead_nr': '30420',
         'lead_date': '2026-09-27', 'timeline': [], 'relations': [], 'answers': ['30420'], 'related': []}
    p.update(over)
    return p


def problems_of(*pages):
    return '\n'.join(bb.check({'version': 1, 'items': {p['id']: p for p in pages}}, ANSWERS))


def test_the_committed_wiki_passes_its_own_check():
    assert bb.check(DOC, ANSWERS) == []


def test_the_shared_schema_exactly():
    assert DOC['version'] == 1 and datetime.fromisoformat(DOC['built']).tzinfo is not None
    assert set(DOC) == {'version', 'built', 'items'}
    for k, e in ITEMS.items():
        assert FIELDS <= set(e) <= FIELDS | {'subject', 'history_da'}, k
        assert ('history_da' in e) == (e['kind'] == 'sag' and k not in bb.load(bb.IDEAS, {}).get('items', {})), k
        assert e['id'] == k and bb.ID.match(k) and e['kind'] in bb.KINDS, k
        assert isinstance(e['case_sensitive'], bool) and all(isinstance(a, str) and a for a in e['aliases']), k
        assert all(set(r) == {'date', 'nr', 'text_da'} for r in e['timeline']), k
        assert all(set(r) == {'with', 'text_da', 'date', 'nr'} for r in e['relations']), k
        assert all(isinstance(n, str) for n in e['answers']) and all(r in ITEMS and r != k for r in e['related']), k
        assert e.get('subject') is None or isinstance(e['subject'], str), k
    # the linker's index is the pages slimmed: name, kind, aliases, case and how many answers
    assert INDEX == json.loads(json.dumps(bb.index_of(DOC)))
    assert set(INDEX) == {'version', 'items'} and set(INDEX['items']) == set(ITEMS)
    for k, v in INDEX['items'].items():
        assert set(v) == {'name', 'kind', 'aliases', 'case_sensitive', 'n_answers'} and v['n_answers'] == len(ITEMS[k]['answers'])


def test_every_text_is_hizb_ut_tahrirs_and_dated():
    for k, e in ITEMS.items():
        for where, t in texts(e):
            assert 'Hizb ut-Tahrir' in t, (k, where, t[:80])
            assert bb.names_a_time(t), (k, where, t[:80])
        assert len(bb.sentences(e['lead_da'])) <= bb.LEAD_SENTENCES, k
        assert e['lead_date'] == ANSWERS[e['lead_nr']]['date'], k
        for r in e['timeline'] + e['relations']:
            assert r['date'] == ANSWERS[r['nr']]['date'], (k, r['nr'])
        dates = [r['date'] for r in e['timeline']]
        assert dates == sorted(dates, reverse=True), k
        assert e['answers'] == bb.newest_first(e['answers'], ANSWERS), k


def test_every_answer_number_is_in_the_movement_index():
    for k, e in ITEMS.items():
        nrs = [e['lead_nr']] + [r['nr'] for r in e['timeline'] + e['relations']] + e['answers']
        assert all(n in ANSWERS for n in nrs), (k, [n for n in nrs if n not in ANSWERS])
        assert len(set(e['answers'])) == len(e['answers']), k
        assert {r['nr'] for r in e['timeline']} | {e['lead_nr']} <= set(e['answers']) | {e['lead_nr']}, k


def test_no_alias_names_two_pages():
    owner = {}
    for k, e in ITEMS.items():
        for a in e['aliases']:
            assert owner.setdefault(a.casefold(), k) == k, f"'{a}' is an alias of both {owner[a.casefold()]} and {k}"


def test_no_alias_is_an_ordinary_danish_word_an_adjective_or_a_word_for_a_people():
    assert len(bb.STOPWORDS) >= 500
    assert {'og', 'det', 'krig', 'regeringen', 'amerikansk', 'israelske', 'russerne', 'jøder', 'muslimer', 'palæstinenserne',
            'kurderne', 'danskerne', 'vesten', 'golf'} <= bb.STOPWORDS
    for k, e in ITEMS.items():
        for a in e['aliases']:
            key = a.casefold()
            assert key not in bb.STOPWORDS, (k, a)
            assert not all(w in bb.FUNCTION_WORDS for w in key.split()), (k, a)
            if ' ' not in key and key not in bb.PEOPLE_OK:
                assert not bb.ADJECTIVE.search(key) and not bb.PEOPLE.search(key), (k, a)
            if e['case_sensitive']:
                assert a[:1].isupper() or a[:1].isdigit(), (k, a)
    # the rule names what it refuses
    refused = bb.alias_problems({'usa': ['amerikanske', 'amerikanerne'], 'israel': ['israelsk', 'jøderne'], 'rusland': ['russerne'],
                                 'palaestina': ['palæstinenserne'], 'yemen': ['yemenitter'], 'x': ['den', 'og så']})
    for a in ('amerikanske', 'amerikanerne', 'israelsk', 'jøderne', 'russerne', 'palæstinenserne', 'yemenitter', 'den', 'og så'):
        assert any(f"alias {a!r}" in p for p in refused), a
    assert bb.alias_problems({'a': ['Iran'], 'b': ['iran']}) and not bb.alias_problems({'iran': ['Iran', 'Den Islamiske Republik Iran']})


def test_a_link_names_a_state_power_group_or_issue_never_a_people():
    aliases = {a for e in ITEMS.values() for a in e['aliases']}
    assert {'Saudi-Arabien', 'Saudiarabien', 'houthierne', 'houthi-oprørerne', 'Ansar Allah', 'Storbritannien', 'USA',
            'Israel', 'EU', 'Nato', 'Hizbollah', 'Grønland', 'krigen i Ukraine'} <= aliases
    assert not aliases & {'amerikansk', 'amerikanske', 'israelsk', 'russerne', 'jøder', 'saudisk', 'Saudi', 'Teheran',
                          'Moskva', 'Washington', 'Det Hvide Hus', 'Trump', 'Selvstyret', 'den jødiske entitet'}
    assert ITEMS['houthierne']['case_sensitive'] is False and ITEMS['iran']['case_sensitive'] is True
    assert ITEMS['israel']['name'] == 'Israel'   # Khabar's own voice says Israel (card H5)


def test_the_voice_rules_hold_and_the_check_catches_what_it_must():
    assert problems_of(page()) == ''
    bad = {
        "not attributed": page(lead_da='Testland er en stat (27/9/2026).'),
        'names no date': page(lead_da='Ifølge Hizb ut-Tahrirs svar er Testland en stat.'),
        "Khabar says 'Israel'": page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er den jødiske entitet her.'),
        "'agentstat'": page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er Testland en agentstat.'),
        'staged or sponsored (G13)': page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 var angrebet i byen iscenesat.'),
        'Kongrespart, H3': page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er Kongrespartiet loyalt over for Storbritannien.'),
        'a quotation over': page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er det »' + 'ord ' * 20 + '«.'),
        'unknown answer': page(lead_nr='999999'),
        'dated 2026-09-26': page(lead_date='2026-09-26'),
        'never peoples': page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er jøderne skyld.'),
        'not newest first': page(timeline=[{'date': '2026-08-18', 'nr': '30170', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 18/8/2026 x.'},
                                           {'date': '2026-09-27', 'nr': '30420', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 27/9/2026 y.'}]),
        'at most 4': page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er det sådan. A. B. C. D.'),
        'lower-case alias on a case-sensitive page': page(aliases=['testlandet']),
        'is no other page': page(related=['findes-ikke']),
    }
    for why, p in bad.items():
        assert why in problems_of(p), why
    assert 'also an alias of' in problems_of(page(), page(id='andetland', name='Andetland', aliases=['testland'], case_sensitive=False))
    # a government or rule may be read; a non-ruling person may not be said to serve (card H3)
    assert problems_of(page(lead_da='Ifølge Hizb ut-Tahrirs svar af 27/9/2026 var styret under Hasina knyttet til Storbritannien.')) == ''


def test_the_newest_answer_governs_the_lead():
    """The owner's examples (2026-10-17): Russia fallen to a middle power (12/6/2026), Britain weakened with only the
    Gulf states and Jordan left (5/8/2026), Iran a US satellite again (28/6/2026), Saudi Arabia subordinate to the USA
    since 2015 – and every page with a current reading in the layer leads with it."""
    ru, gb, ir, sa = (ITEMS[k] for k in ('rusland', 'storbritannien', 'iran', 'saudi-arabien'))
    assert ru['lead_date'] == '2026-06-12' and 'mellemniveau' in ru['lead_da'] and ru['kind'] == 'magt'
    assert gb['lead_date'] == '2026-08-05' and 'Golfstaterne og Jordan' in gb['lead_da']
    assert ir['lead_date'] == '2026-06-28' and 'satellitstat' in ir['lead_da']
    assert 'underordnet stat under USA' in sa['lead_da'] and '2015' in sa['lead_da'] and sa['lead_date'] >= '2026-01-01'
    for k, c in LAYER['current'].items():
        if '--' in k or k in bb.load(bb.IDEAS, {}).get('items', {}):
            continue
        e = ITEMS[k]
        if e['lead_da'] == c['text_da']:     # the current reading leads (a lead without a day rests on the answer it cites)
            assert e['lead_date'] >= c['date'] and bb.cited(e['lead_da'], e['lead_date']), k
        else:                                # a newer reading leads, the current one after it (never a power's)
            assert e['kind'] != 'magt' and e['lead_date'] > c['date'] and e['lead_da'].startswith(e['timeline'][0]['text_da']), k
    # the review of 2026-10-17: the newest reading leads, also where the layer's current reading is older
    assert ITEMS['bahrain']['lead_date'] == ITEMS['qatar']['lead_date'] == ITEMS['oman']['lead_date'] == '2026-08-05'
    assert ITEMS['yemen']['lead_date'] == '2026-09-27' and ITEMS['frankrig']['lead_nr'] == '28073'
    assert ITEMS['usa']['lead_nr'] == '28942'        # the power's standing leads, its newer acts in one arena follow
    for k, e in ITEMS.items():
        assert bb.cited(bb.sentences(e['lead_da'])[0], e['lead_date']), k
        assert not any(w in e['lead_da'] for w in ('Ingen nyere', 'intet nyere', 'ikke gengivet', 'nævnes ikke')), k
    # an issue's lead opens on its newest answers (Iran-sagen: 18/8 and 27/9/2026, then the revision of 28/6/2026); the
    # history behind it stays whole on the page
    sag = ITEMS['iran-sagen']
    assert sag['kind'] == 'sag' and sag['subject'] == 'iran' and sag['lead_date'] == '2026-09-27' and '28/6/2026' in sag['lead_da']
    assert sag['lead_da'].startswith('Ifølge Hizb ut-Tahrirs svar af 18/8/2026 og 27/9/2026') and sag['history_da'].startswith('Fra 2009 til 2025 læser Hizb ut-Tahrirs svar Iran')
    assert '28942' not in {r['nr'] for r in ITEMS['palaestina']['timeline']}
    assert 'Kina' in ITEMS['den-internationale-tilstand']['lead_da'] and 'mellemmagt' in ITEMS['den-internationale-tilstand']['lead_da']


def test_every_subject_of_the_layer_has_its_page():
    for k in set(LAYER['readings']) | set(LAYER['current']):
        if '--' in k:
            continue
        assert ITEMS[k]['subject'] == k and ITEMS[k]['kind'] in ('stat', 'magt', 'gruppe', 'organisation'), k
    for iid in LAYER['issues']:
        pid = f'{iid}-sagen' if iid in ITEMS and ITEMS[iid]['kind'] != 'sag' else iid
        assert ITEMS[pid]['kind'] == 'sag' and ITEMS[pid]['subject'] == iid, iid
        assert ITEMS[pid]['timeline'] and all(r['nr'] in LAYER['issues'][iid]['nrs'] for r in ITEMS[pid]['timeline']), iid
    assert {ITEMS[k]['kind'] for k in ('usa', 'rusland', 'kina', 'storbritannien', 'frankrig', 'tyskland', 'eu')} == {'magt'}
    assert {ITEMS[k]['kind'] for k in ('hamas', 'hizbollah', 'houthierne', 'rsf')} == {'gruppe'}
    assert ITEMS['palaestinensisk-selvstyre']['kind'] == 'organisation'     # the answers: a self-rule, no state


def test_a_relation_is_on_both_parties_pages():
    for k in set(LAYER['readings']) | set(LAYER['current']):
        if '--' not in k:
            continue
        a, b = k.split('--')
        for me, other in ((a, b), (b, a)):
            rows = [r for r in ITEMS[me]['relations'] if r['with'] == other]
            assert len(rows) == 1, (k, me)
            if k in LAYER['current']:
                assert rows[0]['text_da'] == LAYER['current'][k]['text_da'], k
        assert b in ITEMS[a]['related'] and a in ITEMS[b]['related'], k
    assert 'iran-sagen' == ITEMS['iran']['related'][0] and {'afghanistan', 'pakistan'} <= set(ITEMS['afghanistan-pakistan']['related'])


def test_a_timeline_reading_says_when_read_alone():
    """A reading spanning several answers names its span ('fra 12/3/2016 til 29/7/2018'); one reading two syntheses gave
    from one answer is shown once."""
    assert bb.with_date('Ifølge Hizb ut-Tahrirs svar samlede Saudi-Arabien oppositionen.', '2016-03-12', '2018-07-29') == \
        'Ifølge Hizb ut-Tahrirs svar fra 12/3/2016 til 29/7/2018 samlede Saudi-Arabien oppositionen.'
    assert bb.with_date('Ifølge Hizb ut-Tahrirs svar er det sådan.', '2016-03-12') == 'Ifølge Hizb ut-Tahrirs svar af 12/3/2016 er det sådan.'
    rows = [{'date': '2022-03-04', 'nr': '1', 'kind': 'motiv', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 4/3/2022 tror Putin, at Rusland kan '
             'genvinde status som supermagt ved siden af USA, og ser sig som USA\'s ligemand.'},
            {'date': '2022-03-04', 'nr': '1', 'kind': 'tilstand', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 4/3/2022: Putin tror, at Rusland '
             'under de nuværende omstændigheder kan genvinde status som supermagt ved siden af USA og ser sig som USA\'s ligemand.'}]
    assert len(bb.timeline_of(rows)) == 1 and 'omstændigheder' in bb.timeline_of(rows)[0]['text_da']


@needs_seed
def test_the_concepts_merge_with_their_own_entry_winning_a_clash():
    lead = 'Ifølge Hizb ut-Tahrirs svar af 18/8/2026 er det et begreb.'
    ideas = {'version': 1, 'items': {
        'golfen': {'id': 'golfen', 'name': 'Golfen (begreb)', 'kind': 'begreb', 'aliases': ['Golfen'], 'case_sensitive': True,
                   'lead_da': lead, 'lead_nr': '30170', 'lead_date': '2026-08-18', 'timeline': [], 'relations': [],
                   'answers': ['30170', '999999'], 'related': ['iran', 'findes-ikke']},
        'satellitstat': {'id': 'satellitstat', 'name': 'Satellitstat', 'kind': 'begreb', 'aliases': ['satellitstat', 'Iran', 'amerikanske'],
                         'case_sensitive': False, 'lead_da': lead, 'lead_nr': '30170', 'lead_date': '2026-08-18', 'timeline': [],
                         'relations': [], 'answers': ['30170'], 'related': ['saudi-arabien']},
        'uden-kilde': {'id': 'uden-kilde', 'name': 'Uden kilde', 'kind': 'begreb', 'aliases': ['kildeløs'], 'case_sensitive': False,
                       'lead_da': 'Et begreb uden nogen tilskrivning.', 'lead_nr': '30170', 'lead_date': '2026-08-18',
                       'timeline': [], 'relations': [], 'answers': [], 'related': []}}}
    doc, report = bb.build(now=datetime(2026, 10, 17, tzinfo=timezone.utc), ideas=ideas)
    text = '\n'.join(report)
    assert "id clash: the concept 'golfen'" in text and "alias clash: 'Iran' of the page iran" in text
    assert 'uden-kilde lead: not attributed' in text and "alias 'amerikanske'" in text and "'findes-ikke' is no page" in text
    items = doc['items']
    assert items['golfen']['kind'] == 'begreb' and items['golfen']['answers'] == ['30170'] and 'uden-kilde' not in items
    assert 'Iran' not in items['iran']['aliases'] and items['satellitstat']['aliases'] == ['satellitstat', 'Iran']
    assert 'satellitstat' in items['saudi-arabien']['related'] and 'golfen' in items['iran']['related']
    assert bb.check(doc, ANSWERS) == []


@needs_seed
def test_the_build_works_without_the_concept_file_and_the_committed_wiki_is_the_build():
    doc, _ = bb.build(ideas={})
    assert bb.check(doc, ANSWERS) == [] and not any(e['kind'] == 'begreb' for e in doc['items'].values())
    if not bb.IDEAS.exists():
        assert doc['items'] == ITEMS, 'begreber.json is out of date: run py scripts/build_begreber.py'
    fresh, _ = bb.build()
    assert fresh['items'] == ITEMS, 'begreber.json is out of date: run py scripts/build_begreber.py'


def test_the_public_files_hold_no_private_paths_or_long_quotes():
    for name in ('begreber.json', 'begreber-index.json'):
        text = (VIDEN / name).read_text(encoding='utf-8')
        assert not bb.bm.LOCAL.search(text), name
        assert all(len(a or b) <= bb.bm.QUOTE_MAX for a, b in bb.bm.QUOTE.findall(text)), name
        assert not re.search(r'\bClaude\b', text), name     # the app never mentions Claude
