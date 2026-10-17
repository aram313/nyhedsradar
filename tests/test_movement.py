"""The movement layer (public/viden/movement.json, scripts/build_movement.py) keeps the card's hard rules: the committed
layer passes its own check, the check catches what the Khabar 2 critics found (staging claims about attacks, serving
claims about non-ruling persons and parties, agent words, readings without the movement's name, dates that are not
their answer's), the newest answer governs the current readings, and a rebuild from the local extracts gives the
committed layer (ported from the khabar2 branch, 2026-10-17)."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_movement  # noqa: E402

VIDEN = ROOT / 'public' / 'viden'
LAYER = json.loads((VIDEN / 'movement.json').read_text(encoding='utf-8'))


def tiny(**over):
    layer = {'answers': {'1': {'date': '2025-05-15', 'title_da': 't', 'question_da': 'q', 'url': 'https://x.test/1',
                               'note_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 er det en note.'}},
             'readings': {}, 'current': {}, 'issues': {}, 'expectations': []}
    layer.update(over)
    return layer


def test_the_committed_layer_passes_its_own_check():
    assert build_movement.check(LAYER) == []


def test_the_public_files_hold_no_private_paths_long_quotes_or_banned_voice():
    for name in ('movement.json', 'movement-index.json'):
        text = (VIDEN / name).read_text(encoding='utf-8')
        assert not build_movement.LOCAL.search(text), name
        assert all(len(a or b) <= build_movement.QUOTE_MAX for a, b in build_movement.QUOTE.findall(text)), name
        problems = []
        build_movement.check_voice(text, name, problems)
        assert problems == [], problems


def test_every_reading_names_the_movement_and_carries_its_answers_date():
    answers = LAYER['answers']
    for k, a in answers.items():
        assert a['url'] and 'Hizb ut-Tahrir' in a['note_da'], k
    for k, rows in LAYER['readings'].items():
        for r in rows:
            assert 'Hizb ut-Tahrir' in r['text_da'] and r['date'] == answers[r['nr']]['date'], (k, r['nr'])
    for k, c in LAYER['current'].items():
        assert 'Hizb ut-Tahrir' in c['text_da'] and c['date'] == answers[c['nr']]['date'], k
        assert 'Hizb ut-Tahrir' in (c.get('changed_from') or 'Hizb ut-Tahrir'), k
        if c.get('latest_nr'):
            assert c['latest'] == answers[c['latest_nr']]['date'] and c['latest'] > c['date'], k
    assert all('Hizb ut-Tahrir' in v['history_da'] for v in LAYER['issues'].values())
    assert all('Hizb ut-Tahrir' in e['text_da'] for e in LAYER['expectations'])
    # one answer, one date: 366 (Centralasien) is of 19/9/2009 only
    assert '20/10/2010' not in json.dumps(LAYER, ensure_ascii=False)
    assert LAYER['current']['tadsjikistan']['date'] == answers['366']['date'] == '2009-09-19'


def test_the_newest_answer_governs_the_current_readings():
    """The owner's examples: Russia fallen from great power to a middle power (12/6/2026), Britain weakened with only
    the Gulf states and Jordan left (5/8/2026), Iran a US satellite again (28/6/2026), Saudi Arabia subordinate to the
    USA since 2015."""
    cur = LAYER['current']
    assert cur['rusland']['date'] == '2026-06-12' and 'mellemniveau' in cur['rusland']['text_da']
    assert cur['storbritannien']['date'] == '2026-08-05' and 'Golfstaterne og Jordan' in cur['storbritannien']['text_da']
    assert cur['iran']['date'] == '2026-06-28' and 'satellitstat' in cur['iran']['text_da']
    assert cur['saudi-arabien']['since'] == '2015-03-13' and 'underordnet stat under USA' in cur['saudi-arabien']['text_da']


def test_the_check_catches_what_the_critics_found():
    bad = tiny(readings={'indien': [
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 var angrebet i Pahalgam iscenesat.'},
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 er Kongrespartiet loyalt over for Storbritannien.'},
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 er Pakistan USA\'s agentstat.'},
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Svaret læser Indien som underordnet.'},
        {'date': '2025-05-16', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 noget.'}]})
    problems = '\n'.join(build_movement.check(bad))
    assert 'staged or sponsored (G13)' in problems and 'Kongrespart, H3' in problems
    assert "'agentstat'" in problems and 'the movement is not named' in problems and 'dated 2025-05-16' in problems
    ok = tiny(readings={'indien': [
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 gav angrebet i Pahalgam Indien '
         'påskud (svarets påstand om iscenesættelse er ikke gengivet; gerningsbelæg mangler).'},
        {'date': '2025-05-15', 'nr': '1', 'kind': 'k', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 læses Kongres-regeringen som '
         'britisk-loyal, og styret under Hasina var knyttet til Storbritannien.'}]})
    assert build_movement.check(ok) == []
    voice = tiny(issues={'x': {'history_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 er den jødiske entitet og jøderne skyld.', 'nrs': ['1']}})
    problems = '\n'.join(build_movement.check(voice))
    assert "Khabar says 'Israel'" in problems and 'never peoples' in problems


def test_a_bare_reading_gets_the_movements_name_and_date():
    assert build_movement.owned('Svarene læser Yemen som en kampplads.', '2009-11-28', 'fra') == \
        'Hizb ut-Tahrirs svar læser Yemen som en kampplads.'
    assert build_movement.owned('Hæren i Tyrkiet vil ikke opgive magten.', '2004-01-24') == \
        'Ifølge Hizb ut-Tahrirs svar af 24/1/2004: Hæren i Tyrkiet vil ikke opgive magten.'
    assert build_movement.owned('Ifølge svaret er det sådan.', '2004-01-24').startswith('Ifølge Hizb ut-Tahrirs svar af 24/1/2004 ')


def test_the_apps_index_is_the_layer_slimmed():
    index = json.loads((VIDEN / 'movement-index.json').read_text(encoding='utf-8'))
    assert index == json.loads(json.dumps(build_movement.index(LAYER)))
    assert set(index) == {'version', 'built', 'answers', 'current'}
    assert set(index['answers']) == set(LAYER['answers']) and index['current'] == LAYER['current']
    a = index['answers']['30420']
    assert a['date'] == '2026-09-27' and a['title_da'] and a['question_da'] and 'yemen' in a['issues']
    assert 'note_da' not in a and 'url' not in a      # the reader takes these from the full layer


def test_a_change_of_reading_is_dated_only_when_its_dates_are_older():
    """'Siden d/m/åååå · før: …' only where every date in the earlier reading falls before 'since'; a text that spans the
    years after it (or says the standing is unchanged) is the reading's course, 'earlier_da', shown without a date."""
    for k, c in LAYER['current'].items():
        if c.get('changed_from'):
            assert build_movement.changed_before(c['since'], c['changed_from']), k
        assert not (c.get('changed_from') and c.get('earlier_da')), k
    for k in ('jordan', 'usa', 'taiwan', 'pakistan', 'indien--usa'):
        assert 'earlier_da' in LAYER['current'][k] and 'changed_from' not in LAYER['current'][k], k
    assert 'changed_from' in LAYER['current']['saudi-arabien'] and 'changed_from' in LAYER['current']['iran']
    bad = tiny(current={'jordan': {'date': '2025-05-15', 'nr': '1', 'since': '2013-07-21',
                                   'text_da': 'Ifølge Hizb ut-Tahrirs svar af 15/5/2025 er Jordan underordnet.',
                                   'changed_from': 'Ifølge Hizb ut-Tahrirs svar til og med 15/5/2025: Fra 2013 til 2021 britisk.'}})
    assert any("'changed_from' names dates" in p for p in build_movement.check(bad))


def test_every_standing_has_a_class_and_a_break_is_its_own():
    rows = [(k, r) for k, rs in LAYER['readings'].items() for r in rs if r['kind'] == 'stilling' and r.get('value')]
    assert rows and all(r.get('class') == build_movement.stand_class(r['value']) for _, r in rows)
    iran = {r['date']: r for r in LAYER['readings']['iran'] if r['kind'] == 'stilling'}
    assert iran['2026-04-04']['class'] == 'brud' and iran['2026-06-03']['class'] == 'uklar' and iran['2026-06-28']['class'] == 'bundet'
    assert build_movement.stand_class('britisk rest (Golfstaterne samlet)') == 'rest'
    assert build_movement.stand_class('underordnet (i Syrien-sagen)') == 'bundet'
    jordan = next(r for r in LAYER['readings']['jordan'] if r['nr'] == '28157')
    assert jordan.get('historical') is True


def test_the_build_reads_this_branchs_files():
    assert build_movement.OUT == VIDEN / 'movement.json' and build_movement.INDEX == VIDEN / 'movement-index.json'
    assert build_movement.QA == ROOT / 'docs' / 'hjerne' / 'qa-index.json'
    assert not re.search(r'khabar2', (ROOT / 'scripts' / 'build_movement.py').read_text(encoding='utf-8'))


@pytest.mark.skipif(not (build_movement.SRC / 'extract').exists() or not build_movement.QA.exists(),
                    reason='the local extracts (.cache/movement) are not here')
def test_a_rebuild_from_the_extracts_gives_the_committed_layer():
    layer, _, _ = build_movement.build(datetime.fromisoformat(LAYER['built']))
    assert json.loads(json.dumps(layer, ensure_ascii=False)) == LAYER


def test_no_working_label_reaches_a_reading():
    # 'ÆNDRING: redskabet skifter …' was a label of the syntheses, not the movement's words (pro-plan 3.8): every Danish
    # text of the layer and the wiki is free of an all-caps label before a colon, the known acronyms excepted
    label = re.compile(r'(?<![\w])(?!(?:' + '|'.join(build_movement.ACRONYMS) + r')\b)[A-ZÆØÅ]{4,}:')
    for name in ('movement.json', 'begreber.json'):
        text = (VIDEN / name).read_text(encoding='utf-8')
        assert not label.findall(text), (name, label.findall(text)[:5])
    assert build_movement.unlabel('afskåret. ÆNDRING: redskabet skifter. NATO: nej.') == 'afskåret. Redskabet skifter. NATO: nej.'
