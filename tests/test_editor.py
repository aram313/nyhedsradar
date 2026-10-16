"""The editor's tools: the recap of the day, which wire lines it is given, what publishing writes, the 15-minute check,
small updates that keep the front page, the content rules and Hizb ut-Tahrir's new answers."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import brain  # noqa: E402
import editor  # noqa: E402
import voice  # noqa: E402

NOW = '2026-10-10T20:01:00+00:00'   # 22.01 Danish summer time


def wire(i, hhmm, text):
    return {'i': i, 't': f'نص {i}', 'tr': text, 'p': f'2026-10-10T{hhmm}:00+00:00', 'u': f'https://t.me/ajanews/{i}', 'k': 'w'}


TODAY = {'date': '2026-10-10', 'title': 'Politiske nyheder – 10. oktober 2026', 'created': '2026-10-10T11:35:00+00:00',
         'updates': ['2026-10-10T11:35:00+00:00'], 'ids': ['w1'], 'topics': [
             {'name': 'Ukraine', 'section': 'world', 'lines': [
                 {'who': 'Kyivs borgmester', 'text': 'Fire såret.', 'link': 'https://t.me/ajanews/w1', 'source': 'Al Jazeera',
                  'at': '2026-10-10T08:00:00+00:00', 'added': '2026-10-10T11:35:00+00:00', 'id': 'w1', 'kind': 'w'}]}]}
# a small movement layer: short dated readings as public/viden/movement.json holds them
LAYER = {'version': 1, 'answers': {
    '30420': {'date': '2026-09-27', 'title_da': 'Svar på spørgsmål: Rækkevidden af de militære udviklinger i Yemen'},
    '29870': {'date': '2026-06-28', 'title_da': 'Svar på spørgsmål: Den aktuelle virkelighed i Iran'},
    '29773': {'date': '2026-06-12', 'title_da': 'Svar på spørgsmål: Ukraines angreb på Rusland'},
    '28942': {'date': '2026-01-14', 'title_da': "Svar på spørgsmål: USA's sikkerhedsstrategi"}},
    'readings': {}, 'current': {
        'usa': {'text_da': 'Ifølge Hizb ut-Tahrirs svar af 14/1/2026 er USA den førende stat. Svaret siger mere.',
                'date': '2026-01-14', 'nr': '28942'},
        'rusland': {'text_da': 'Ifølge Hizb ut-Tahrirs svar af 12/6/2026 er Rusland faldet fra stormagt til en magt på mellemniveau.',
                    'date': '2026-06-12', 'nr': '29773'},
        'iran': {'text_da': "Ifølge Hizb ut-Tahrirs svar af 28/6/2026 vender Iran tilbage til sin tidligere stilling i USA's bane.",
                 'date': '2026-06-28', 'nr': '29870'},
        'saudi-arabien': {'text_da': 'Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er Saudi-Arabien en underordnet stat under USA.',
                          'date': '2026-09-27', 'nr': '30420'},
        'iran--usa': {'text_da': 'Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er forhandlingerne mellem Iran og USA fastlåst.',
                      'date': '2026-09-27', 'nr': '30420'},
        'danmark': {'text_da': 'Hizb ut-Tahrirs svar har ingen nutidig stillingslæsning af Danmark.', 'date': '2023-08-03',
                    'nr': '24897'}}}


@pytest.fixture
def viden(tmp_path, monkeypatch):
    """The brain reads a small movement layer, no concept pages and no method config: the tests never depend on the
    live files in public/viden or on the radar's weighing module."""
    v = tmp_path / 'viden'
    v.mkdir()
    (v / 'movement.json').write_text(json.dumps(LAYER), encoding='utf-8')
    monkeypatch.setattr(brain, 'VIDEN', v)
    monkeypatch.setattr(brain, 'METHOD', tmp_path / 'no-method.json')
    monkeypatch.setattr(brain, '_method', [None])   # tiers only from the stories themselves, as the radar gives them
    return v


@pytest.fixture
def folder(tmp_path, monkeypatch, viden):
    monkeypatch.setattr(editor, 'WORK', tmp_path / 'work')
    d = tmp_path / 'in'
    d.mkdir()
    (d / 'data.json').write_text(json.dumps({'items': [
        {'id': 's1', 'title': 'Regeringen strammer reglerne', 'summary': '', 'link': 'https://dr.test/1', 'source': 'DR',
         'sec': 'dk', 'rank': 90, 'confirmed': 3, 'published': '2026-10-10T12:00:00+00:00', 'found': '2026-10-10T12:01:00+00:00'},
        {'id': 's4', 'title': 'Kun på Telegram', 'summary': '', 'link': 'https://t.me/x/4', 'source': 'Kanal', 'sec': 'me',
         'rank': 70, 'confirmed': 0, 'published': '2026-10-10T19:30:00+00:00', 'found': '2026-10-10T19:31:00+00:00'},
        {'id': 's3', 'title': 'Already looked at at 13.35', 'summary': '', 'link': 'https://x.test/3', 'source': 'BBC',
         'sec': 'world', 'rank': 95, 'published': '2026-10-10T09:00:00+00:00', 'found': '2026-10-10T09:01:00+00:00'},
        {'id': 's2', 'title': 'Old story', 'summary': '', 'link': 'https://x.test/2', 'source': 'BBC', 'sec': 'world',
         'rank': 99, 'published': '2026-10-09T09:00:00+00:00', 'found': '2026-10-09T09:01:00+00:00'}]}), encoding='utf-8')
    (d / 'lines.json').write_text(json.dumps({'items': [
        wire('w1', '08:00', 'Kyiv mayor: four hurt'), wire('w2', '11:32', 'arrived after the last update was made'),
        wire('w3', '19:00', 'Kremlin: talks go on'), wire('w4', '19:05', 'Kremlin: talks continue'),
        {'i': 'h1', 't': 'Trump: x', 'p': '2026-10-10T19:00:00+00:00', 'u': 'https://x.test/h', 'k': 'h'}]}), encoding='utf-8')
    (d / 'moves.json').write_text(json.dumps({'days': [TODAY]}), encoding='utf-8')
    return d


def publish(folder, tmp_path, draft, now=NOW):
    path = tmp_path / 'update.json'
    path.write_text(json.dumps(draft), encoding='utf-8')
    editor.main(['publish', str(path), '--dir', str(folder), '--now', now, '--out', str(tmp_path / 'out')])
    return (json.loads((tmp_path / 'out' / n).read_text(encoding='utf-8')) for n in ('digest.json', 'moves.json'))


def add_items(folder, *items):
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    data['items'] += list(items)
    (folder / 'data.json').write_text(json.dumps(data), encoding='utf-8')


def story(sid, title, found, **kw):
    return {'id': sid, 'title': title, 'summary': '', 'link': f'https://x.test/{sid}', 'source': 'Reuters', 'sec': 'world',
            'rank': 80, 'confirmed': 2, 'outlets': 1, 'published': found, 'found': found, **kw}


def check(folder, capsys, now=NOW):
    editor.main(['check', '--dir', str(folder), '--now', now])
    return capsys.readouterr().out.strip().splitlines()


YESTERDAY = {**TODAY, 'date': '2026-10-09', 'title': 'Politiske nyheder – 9. oktober 2026',
             'created': '2026-10-09T19:01:00+00:00', 'updates': ['2026-10-09T19:01:00+00:00'], 'ids': []}


def test_input_shows_the_recap_so_far_top_stories_and_new_material(folder):
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert 'The recap of 10. oktober 2026 so far – 1 lines' in text and '### Ukraine (world)' in text
    assert '## Top stories of the last 24 hours' in text and '[s3] world · rank 95' in text   # top stories for picks
    w = text.split('## Al Jazeera wire lines')[1]
    assert '[w2]' in w and '[w3]' in w and '[w1]' not in w and '[h1]' not in w
    new = text.split('for recap lines')[1].split('## Stories to summarise')[0]
    assert '[s1]' in new and '[s3]' not in new and '[s2]' not in new   # only what came after the last update
    assert 'update.json' in text


def test_publish_adds_lines_and_the_editors_notes(folder, tmp_path):
    digest, moves = publish(folder, tmp_path, {
        'topics': [{'name': 'Statsborgerskab', 'section': 'dk', 'lines': [
                       {'who': 'Regeringen', 'text': 'Reglerne for statsborgerskab skal strammes.', 'story': 's1'}]},
                   {'name': 'ukraine ', 'lines': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'ids': ['w3', 'w4']}]}],
        'order': ['Statsborgerskab', 'Ukraine'], 'lede': 'Dagen kort.',
        'picks': [{'id': 's3', 'why': 'Stormagter'}], 'moves': [{'id': 's4', 'sec': 'world'}],
        'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world', 'ids': ['w3']}]})
    assert digest['date'] == '2026-10-10' and [tp['name'] for tp in digest['topics']] == ['Statsborgerskab', 'Ukraine']
    assert [x['who'] for x in digest['topics'][1]['lines']] == ['Kreml', 'Kyivs borgmester']   # continued, newest first
    assert digest['ids'] == ['w1', 'w2', 'w3', 'w4']   # w2 was given and left out: done all the same
    assert digest['updates'] == ['2026-10-10T11:35:00+00:00', '2026-10-10T20:01:00+00:00']
    assert digest['editor'] == {'created': '2026-10-10T20:01:00+00:00', 'lede': 'Dagen kort.', 'lede_at': '2026-10-10T20:01:00+00:00',
                                'picks': [{'id': 's3', 'why': 'Stormagter'}], 'moves': [{'id': 's4', 'sec': 'world'}],
                                'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world',
                                            'link': 'https://t.me/ajanews/w3'}]}
    assert digest['push']['title'] == 'Khabar · dagens resumé, 10. oktober'   # the evening update tells the phones
    assert moves['days'][0]['date'] == '2026-10-10' and 'editor' not in moves['days'][0]
    assert json.loads((tmp_path / 'out' / 'answers.json').read_text(encoding='utf-8')) == {'items': {}}


def test_at_seven_the_night_before_midnight_completes_yesterday(folder, tmp_path):
    (folder / 'moves.json').write_text(json.dumps({'days': [TODAY]}), encoding='utf-8')
    late = {'i': 'w9', 't': 'نص', 'tr': '', 'p': '2026-10-10T21:30:00+00:00', 'u': 'https://t.me/ajanews/w9', 'k': 'w'}   # 23.30
    early = {'i': 'w8', 't': 'نص', 'tr': '', 'p': '2026-10-11T03:00:00+00:00', 'u': 'https://t.me/ajanews/w8', 'k': 'w'}   # 05.00
    items = json.loads((folder / 'lines.json').read_text(encoding='utf-8'))['items'] + [late, early]
    (folder / 'lines.json').write_text(json.dumps({'items': items}), encoding='utf-8')
    digest, moves = publish(folder, tmp_path, {'topics': [{'name': 'Ukraine', 'lines': [
        {'who': 'Kreml', 'text': 'Sent i går.', 'ids': ['w9']}, {'who': 'Kyiv', 'text': 'Tidligt i dag.', 'ids': ['w8']}]}], 'lede': 'Natten kort.'},
        now='2026-10-11T05:02:00+00:00')
    by_date = {d['date']: d for d in moves['days']}
    assert [x['text'] for x in by_date['2026-10-10']['topics'][0]['lines']][:1] == ['Sent i går.']
    assert [x['text'] for x in by_date['2026-10-11']['topics'][0]['lines']] == ['Tidligt i dag.']
    assert digest['date'] == '2026-10-11' and digest['push'] is None   # only the evening update notifies


def test_publish_refuses_what_does_not_fit(folder, tmp_path, capsys):
    bad = {'topics': [{'name': 'Gaza', 'section': 'gaza', 'lines': [
        {'who': '', 'text': 'Uden afsender.', 'ids': ['w1']},             # w1 was looked at this morning
        {'who': 'Kanal', 'text': 'x' * 300, 'story': 's9'},
        {'who': 'Kreml', 'text': 'To gange.', 'ids': ['w3', 'w3']}]}],
        'order': ['Gaza', 'Sudan'], 'picks': [{'id': 'nope'}], 'moves': [{'id': 's1', 'sec': 'mars'}]}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, bad)
    out = capsys.readouterr().out
    for problem in ('section must be dk, me or world', 'needs who and text', "'w1' is no new wire line", 'is too long',
                    "unknown story id 's9'", 'wire line w3 is used twice', "order: 'Sudan' is no topic",
                    "picks: unknown story id 'nope'", 'moves:', 'there is no lede to keep'):
        assert problem in out, problem


def test_editions_from_before_days_become_days():
    moves = {'briefs': [
        {'created': '2026-10-10T13:03:00+00:00', 'ids': ['w3'], 'topics': [{'name': 'Gaza', 'section': 'me', 'stories': [
            {'id': 's1', 'headline': 'Syv dræbt', 'text': '…', 'link': 'https://aj.test/1', 'source': 'Al Jazeera',
             'confirmed': 3}], 'lines': [{'who': 'WAFA', 'text': 'Valget er udskudt.', 'link': 'https://t.me/ajanews/w3', 'id': 'w3'}]}]},
        {'created': '2026-10-10T05:00:00+00:00', 'until': '2026-10-10T05:00:00+00:00', 'topics': []}]}
    days = editor.migrate(moves, {'items': []}, {'items': [wire('w3', '12:40', '')]})['days']
    assert [d['date'] for d in days] == ['2026-10-10']
    assert days[0]['updates'] == ['2026-10-10T05:00:00+00:00', '2026-10-10T13:03:00+00:00']
    assert days[0]['ids'] == ['w3'] and days[0]['until'] == '2026-10-10T05:00:00+00:00'
    assert [(x['who'], x['text'], x['kind']) for x in days[0]['topics'][0]['lines']] == [
        ('', 'Syv dræbt', 's'), ('WAFA', 'Valget er udskudt.', 'w')]   # the story by its edition's time, the line by its own
    lines = {'items': [wire('a', '04:00', ''), wire('b', '12:00', ''), wire('w3', '12:40', '')]}
    assert [v['i'] for v in editor.uncovered(lines, {'days': days})] == ['b']


def test_window_starts_at_the_last_update():
    t = editor.ts
    now = t('2026-10-10T13:01:00+00:00')
    assert editor.window_start(now, ['2026-10-10T05:02:00+00:00']) == t('2026-10-10T05:02:00+00:00')
    assert editor.window_start(now, []) == t('2026-10-10T01:01:00+00:00')                                # 12 hours back
    assert editor.window_start(now, ['2026-10-09T05:00:00+00:00']) == t('2026-10-10T01:01:00+00:00')  # too old to count


def test_summaries_are_asked_for_checked_and_kept(folder, tmp_path):
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    asked = text.split('## Stories to summarise')[1].split('## Al Jazeera')[0]
    assert '[s1]' in asked and '[s2]' not in asked   # yesterday's story is no longer opened much
    (folder / 'summaries.json').write_text(json.dumps({'items': {
        'old': {'text': 'Gammelt.', 'paywall': False, 'at': '2026-10-01T10:00:00+00:00'},
        's3': {'text': 'Fra i formiddags.', 'paywall': False, 'at': '2026-10-10T11:35:00+00:00'}}}), encoding='utf-8')
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'summaries': [
        {'id': 's1', 'text': 'Regeringen vil stramme reglerne. Forslaget kommer i næste uge.', 'paywall': True}]})
    kept = json.loads((tmp_path / 'out' / 'summaries.json').read_text(encoding='utf-8'))['items']
    assert set(kept) == {'s1', 's3'} and kept['s1']['paywall'] is True   # older than four days: dropped
    digest = json.loads((tmp_path / 'out' / 'digest.json').read_text(encoding='utf-8'))
    assert 'summaries' not in digest['editor']


def test_a_summary_must_fit(folder, tmp_path, capsys):
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'summaries': [
            {'id': 'nope', 'text': 'x'}, {'id': 's1', 'text': 'x' * 500}, {'id': 's3', 'text': 'Kort.', 'paywall': 'måske'}]})
    out = capsys.readouterr().out
    assert "unknown story id 'nope'" in out and 'at most 420' in out and 'paywall must be true or false' in out


def test_machine_headlines_are_asked_for_checked_and_kept(folder, tmp_path):
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    data['items'][2].update(lang='en', title_da='Allerede set kl. 13.35')   # s3, gone over this morning
    data['items'].append({'id': 's5', 'title': 'نص', 'title_tr': 'Text', 'title_da': 'Tekst', 'lang': 'ar', 'summary': '',
                          'link': 'https://aj.test/5', 'source': 'Al Jazeera', 'sec': 'me', 'rank': 60,
                          'published': '2026-10-10T18:00:00+00:00', 'found': '2026-10-10T18:01:00+00:00'})
    (folder / 'data.json').write_text(json.dumps(data), encoding='utf-8')
    (folder / 'summaries.json').write_text(json.dumps({'items': {}, 'titles': {
        's3': {'title': 'Set i formiddags', 'at': '2026-10-10T11:35:00+00:00'},
        'old': {'title': 'Gammel', 'at': '2026-10-01T10:00:00+00:00'}}}), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    asked = text.split('## Danish headlines to check')[1].split('## Al Jazeera')[0]
    assert '[s5] ar · نص (English: Text) → Tekst' in asked
    assert '[s3]' not in asked and '[s1]' not in asked   # gone over already; Danish to begin with
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'titles': [{'id': 's5', 'title': 'Teksten  på dansk'}]})
    out = json.loads((tmp_path / 'out' / 'summaries.json').read_text(encoding='utf-8'))
    assert set(out['titles']) == {'s3', 's5'} and out['titles']['s5']['title'] == 'Teksten på dansk'   # older than four days: dropped
    assert 'titles' not in json.loads((tmp_path / 'out' / 'digest.json').read_text(encoding='utf-8'))['editor']


def test_a_headline_must_fit(folder, tmp_path, capsys):
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'titles': [
            {'id': 'nope', 'title': 'x'}, {'id': 's1', 'title': 'x' * 200}, {'id': 's3', 'title': ' '}]})
    out = capsys.readouterr().out
    assert "titles: unknown story id 'nope'" in out and 'at most 140' in out and 'not 0' in out


def test_opened_stories_are_summarised_first_and_yesterday_shrinks(folder, tmp_path):
    (folder / 'learned.json').write_text(json.dumps([{'id': 's4', 'why': 'read', 'at': '2026-10-10T19:00:00+00:00'},
                                                      {'id': 's1', 'why': 'community', 'at': '2026-10-10T19:00:00+00:00'}]), encoding='utf-8')
    (folder / 'moves.json').write_text(json.dumps({'days': [YESTERDAY, TODAY]}), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])   # 22.01: yesterday is done
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    asked = text.split('## Stories to summarise')[1].split('## ')[0]
    assert asked.index('[s4]') < asked.index('[s1]')          # opened by a reader: first, though weaker
    assert '[s1] – listed above' in asked and 'curl' not in text and 'Stories without a picture' not in text
    assert "## Yesterday's topics (9. oktober 2026, 1 lines)" in text and '- Ukraine (world)' in text
    assert 'The recap of 9. oktober' not in text and 'The recap of 10. oktober 2026 so far' in text
    editor.main(['input', '--dir', str(folder), '--now', '2026-10-10T05:01:00+00:00'])   # 07.01: yesterday in full
    assert 'The recap of 9. oktober 2026 so far' in (editor.WORK / 'input.md').read_text(encoding='utf-8')


def test_only_the_first_update_after_21_notifies():
    day = {'topics': [{'name': 'X', 'lines': [{'who': 'A', 'text': 'b'}]}],
           'updates': ['2026-10-10T19:01:00+00:00', '2026-10-10T20:01:00+00:00']}   # 21.01 and 22.01 Danish time
    assert editor.push_text(day, editor.ts('2026-10-10T19:01:00+00:00')) is not None
    assert editor.push_text(day, editor.ts('2026-10-10T20:01:00+00:00')) is None
    assert editor.push_text(day, editor.ts('2026-10-10T18:01:00+00:00')) is None


# ------------------------------------------------------------------ the check every quarter of an hour

def test_check_says_what_is_new_and_when_to_update(folder, capsys):
    add_items(folder, story('b1', 'Big story', '2026-10-10T19:50:00+00:00', big=True, outlets=6, tier=2, sec='me',
                            title_da='Trump truer Iran'),
              story('t3', 'Two outlets', '2026-10-10T19:40:00+00:00', outlets=2, tier=3, title_da='Kina sender flåde'),
              story('t9', 'Small', '2026-10-10T19:45:00+00:00', outlets=1, tier=9, title_da='Olieprisen stiger'))
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': {
        'created': '2026-10-10T11:35:00+00:00', 'lede': 'Formiddagens lede.', 'picks': [{'id': 's3', 'why': 'x'}]}}), encoding='utf-8')
    out = check(folder, capsys)
    assert len(out) <= 40 and out[1].startswith('Last full update: 10.10 13.35 (8 t 26 min ago)')
    assert 'tier 2 · 6 outlets · big · me · 21.50 · Trump truer Iran' in out[3]       # the heaviest first
    assert 'tier 3 · 2 outlets · world' in out[4] and not any('Olieprisen' in x for x in out)   # tier 9, one outlet: no weight
    assert '  Lede (10.10 13.35): Formiddagens lede.' in out and '  Pick 1: Already looked at at 13.35' in out
    assert out[-1].startswith('OPDATÉR: stor historie siden sidst: Trump truer Iran; tier 3 med 2 medier: Kina sender flåde')
    assert '8 t 26 min siden sidste opdatering' in out[-1] and 'dagens resumé til telefonerne' in out[-1]


def test_check_is_quiet_when_nothing_of_weight_came(folder, capsys):
    out = check(folder, capsys, now='2026-10-10T12:30:00+00:00')   # 14.30, the last update 55 minutes ago
    assert out[-1] == 'INTET NYT AF VÆGT' and 'New since 13.35: 1 stories, 0 grew · 0 of weight' in out[2]
    night = {**TODAY, 'date': '2026-10-11', 'updates': ['2026-10-10T22:03:00+00:00'], 'topics': [], 'ids': ['w1', 'w2', 'w3', 'w4']}
    (folder / 'moves.json').write_text(json.dumps({'days': [night, TODAY]}), encoding='utf-8')
    assert check(folder, capsys, now='2026-10-11T01:00:00+00:00')[-1] == 'INTET NYT AF VÆGT'   # 03.00: no clock at night
    morning = check(folder, capsys, now='2026-10-11T04:05:00+00:00')                          # 06.05: the day's first
    assert morning[-1] == 'OPDATÉR: første kørsel efter kl. 6: dagens forside'


def test_check_sees_a_story_that_grew_big_since_the_last_update(folder, capsys):
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    data['items'][2].update(big=True, outlets=4, members=['s3', 'a1', 'a2', 'a3', 'a4'],
                            also=[{'id': 'a1', 'source': 'AP', 'title': 'x'},
                                                        {'id': 'a2', 'source': 'AFP', 'title': 'y'},
                                                        {'id': 'a3', 'source': 'DR', 'title': 'z'}])   # s3, found 11.01
    (folder / 'data.json').write_text(json.dumps(data), encoding='utf-8')
    (folder / 'items.json').write_text(json.dumps({'s3': {'found': '2026-10-10T09:01:00+00:00', 'source': 'BBC'},
                                                   'a1': {'found': '2026-10-10T09:30:00+00:00', 'source': 'AP'},
                                                   'a2': {'found': '2026-10-10T15:00:00+00:00', 'source': 'AFP'},
                                                   'a3': {'found': '2026-10-10T16:00:00+00:00', 'source': 'DR'},
                                                   'a4': {'found': '2026-10-10T16:10:00+00:00', 'source': 'AP'}}),
                                       encoding='utf-8')   # a4: AP's second article – no new outlet
    out = check(folder, capsys, now='2026-10-10T16:30:00+00:00')
    assert any('4 outlets (+2 since) · big · world' in x for x in out)        # two outlets then: it became big since
    assert out[-1].startswith('OPDATÉR: stor historie siden sidst: Already looked at at 13.35')
    editor.main(['input', '--dir', str(folder), '--now', '2026-10-10T16:30:00+00:00'])
    new = (editor.WORK / 'input.md').read_text(encoding='utf-8').split('for recap lines')[1].split('## Stories to summarise')[0]
    assert '[s3] world · rank 95 · big · 4 outlets (+2 since the last update)' in new


# ------------------------------------------------------------------ the brain in the input

def test_the_brain_weighs_by_the_books_and_the_newest_answers(viden):
    top = [story('x1', 'Iran og USA forhandler i Oman', '2026-10-10T18:00:00+00:00', tier=1),
           story('x2', 'Iranske styrker øver ved Hormuz – USA sender skibe', '2026-10-10T17:00:00+00:00', tier=2),
           story('x3', 'Saudi-Arabiens kronprins mødes med Erdoğan', '2026-10-10T16:00:00+00:00', tier=5),
           story('x4', 'Danmarks regering vil stramme', '2026-10-10T15:00:00+00:00', tier=12)]
    noted = {'30555': {'nr': '30555', 'date': '2026-10-09', 'title_da': 'Svar på spørgsmål: Iran efter krigen'}}
    lines = brain.section(top, noted)
    text = '\n'.join(lines)
    assert len(text) <= brain.BUDGET and 'The app shows no analysis' in text
    assert "### The books' order of weight (heaviest first) – each story's tier is in the lists below" in text
    assert '1 sign of change in the international situation' in text and '13 weighed down' in text
    assert "Danish politics is never buried" in text
    state = text.split('### Den internationale tilstand ifølge Hizb ut-Tahrirs nyeste svar')[1].split('###')[0]
    assert '- USA (nr 28942): Ifølge Hizb ut-Tahrirs svar af 14/1/2026 er USA den førende stat.' in state   # first sentence
    assert 'Svaret siger mere' not in state and state.index('- USA') < state.index('- Rusland')         # the leading state first
    named = text.split("### Named in today's top stories")[1].split('###')[0]
    assert "- Iran · 2 stories (nr 29870): Ifølge Hizb ut-Tahrirs svar af 28/6/2026 vender Iran" in named
    assert '- Saudi-Arabien · 1 story (nr 30420)' in named and '- USA ·' not in named        # the powers stand above
    assert '- Danmark · 1 story (3/8/2023, nr 24897): Hizb ut-Tahrirs svar har ingen nutidig' in named   # dated
    assert '- Iran – USA · 2 stories (nr 30420): Ifølge Hizb ut-Tahrirs svar af 27/9/2026' in named
    newest = text.split("### Hizb ut-Tahrir's newest answers")[1]
    assert newest.index('9/10/2026 · nr 30555 · Iran efter krigen') < newest.index('27/9/2026 · nr 30420 · Rækkevidden')
    assert 'Ukraines angreb' not in newest   # three only


def test_the_brain_names_by_the_concept_pages_when_they_are_built(viden):
    (brain.VIDEN / 'begreber-index.json').write_text(json.dumps({'version': 1, 'items': {
        'normalisering': {'name': 'Normalisering', 'kind': 'proces', 'aliases': ['normaliseringen', 'normalisering'],
                          'case_sensitive': False, 'n_answers': 9},
        'iran': {'name': 'Iran', 'kind': 'stat', 'aliases': ['Iran', 'iranske'], 'case_sensitive': True, 'n_answers': 80}}}),
        encoding='utf-8')
    (brain.VIDEN / 'begreber.json').write_text(json.dumps({'version': 1, 'items': {
        'normalisering': {'id': 'normalisering', 'name': 'Normalisering', 'lead_da': 'Ifølge Hizb ut-Tahrirs svar af 2/5/2026 '
                          'vil USA give Israel en ledende rolle gennem normaliseringen. Mere tekst.', 'lead_nr': '29572',
                          'lead_date': '2026-05-02'}}}), encoding='utf-8')
    top = [story('x1', 'Normaliseringen med Israel drøftes i Riyadh', '2026-10-10T18:00:00+00:00'),
           story('x2', 'iranske droner over Irak', '2026-10-10T17:00:00+00:00'),
           story('x3', 'Saudi-Arabien køber fly', '2026-10-10T16:00:00+00:00')]
    named = '\n'.join(brain.section(top)).split("### Named in today's top stories")[1].split('###')[0]
    assert '- Normalisering · 1 story (nr 29572): Ifølge Hizb ut-Tahrirs svar af 2/5/2026 vil USA give Israel' in named
    assert 'Mere tekst' not in named
    assert '- Iran · 1 story (nr 29870)' in named               # no page lead yet: the layer's current reading
    assert 'Saudi-Arabien' not in named                          # the index names the subjects now


def test_the_brain_keeps_to_its_budget_and_its_lines_dated(viden):
    top = [story(f'x{n}', 'Iran og USA, Saudi-Arabien og Danmark', '2026-10-10T18:00:00+00:00') for n in range(3)]
    full = '\n'.join(brain.section(top))
    assert '- Iran – USA · 3 stories' in full and '- Danmark · 3 stories' in full
    small = '\n'.join(brain.section(top, budget=len(full) - 40))
    assert len(small) <= len(full) - 40 and '- Iran – USA' not in small and '- Danmark · 3 stories' in small   # pairs go first
    assert '13 weighed down' in small and '- Rusland (nr 29773)' in small           # the order and the powers stay
    long = 'Ifølge Hizb ut-Tahrirs svar af 5/8/2026 mistede Storbritannien Irak i 2003 ' + 'og meget mere ' * 12 + '; resten.'
    assert brain.one_line('2026-08-05', '30093', long, limit=220).endswith('…')
    clause = 'Ifølge Hizb ut-Tahrirs svar af 5/8/2026 har Storbritannien kun Golfstaterne tilbage; ' + 'x ' * 120
    assert brain.one_line('2026-08-05', '30093', clause) == '(nr 30093): Ifølge Hizb ut-Tahrirs svar af 5/8/2026 har ' \
                                                           'Storbritannien kun Golfstaterne tilbage'
    assert brain.one_line('2025-01-23', '', 'Partiet er skubbet til side.') == \
        '(23/1/2025): Ifølge Hizb ut-Tahrirs svar af 23/1/2025: Partiet er skubbet til side.'


def test_the_input_carries_the_brain_and_the_front_page(folder):
    add_items(folder, story('x1', 'Iran og USA forhandler', '2026-10-10T18:00:00+00:00', tier=1, outlets=3))
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': {
        'created': '2026-10-10T11:35:00+00:00', 'lede': 'Formiddagens lede.', 'picks': [{'id': 'x1', 'why': 'x'}],
        'moves': [], 'quotes': []}}), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert text.index('## The brain') < text.index('## The front page now') < text.index('## The recap of')
    assert 'Lede (written 10.10 13.35): Formiddagens lede.' in text and 'Pick 1: [x1] tier 1 · Iran og USA forhandler' in text
    assert '[x1] world · tier 1 · rank 80 · 3 outlets' in text and '## How small an update can be' in text
    assert '"answer"' not in text.split('## Write /tmp/editor/update.json')[1]   # no answer waiting


# ------------------------------------------------------------------ small updates keep the front page

FRONT = {'created': '2026-10-10T11:35:00+00:00', 'lede': 'Formiddagens lede.', 'lede_at': '2026-10-10T11:35:00+00:00',
         'picks': [{'id': 's3', 'why': 'x'}, {'id': 'gone', 'why': 'y'}], 'moves': [{'id': 's4', 'sec': 'world'}],
         'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world', 'link': 'https://t.me/ajanews/w3'}]}


def test_a_small_update_keeps_the_lede_picks_quotes_and_moves(folder, tmp_path):
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': FRONT}), encoding='utf-8')
    digest, _ = publish(folder, tmp_path, {'topics': [{'name': 'Ukraine', 'lines': [
        {'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'ids': ['w3']}]}]})
    e = digest['editor']
    assert e['lede'] == 'Formiddagens lede.' and e['lede_at'] == '2026-10-10T11:35:00+00:00' and e['created'] == NOW
    assert e['picks'] == [{'id': 's3', 'why': 'x'}]                       # a pick the radar dropped goes
    assert e['moves'] == [{'id': 's4', 'sec': 'world'}] and e['quotes'] == FRONT['quotes']
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': e}), encoding='utf-8')
    digest, _ = publish(folder, tmp_path, {'lede': 'keep', 'picks': 'keep', 'moves': [{'id': 's4', 'sec': 'me'}],
                                           'quotes': []}, now='2026-10-10T20:16:00+00:00')
    assert digest['editor']['moves'] == [] and digest['editor']['quotes'] == []   # back in its own section; quotes cleared
    assert digest['editor']['lede'] == 'Formiddagens lede.'


def test_yesterdays_lede_is_not_kept_after_six(folder, tmp_path, capsys):
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': {**FRONT, 'lede_at': '2026-10-09T19:00:00+00:00'}}),
                                        encoding='utf-8')
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {}, now='2026-10-10T05:00:00+00:00')     # 07.00
    assert 'the lede on the front page is from an earlier day' in capsys.readouterr().out
    digest, _ = publish(folder, tmp_path, {}, now='2026-10-09T23:30:00+00:00')   # 01.30: the night keeps last evening's
    assert digest['editor']['lede'] == 'Formiddagens lede.'


def test_the_editors_own_text_stays_reality_and_keeps_the_rules(folder, tmp_path, capsys):
    bad = {'lede': "Iran, nu USA's satellit, forhandler med Washington.",
           'summaries': [{'id': 's1', 'text': 'Ifølge Hizb ut-Tahrirs svar af 27/9/2026 er planen amerikansk.', 'paywall': True}],
           'quotes': [{'who': 'Hamas', 'text': 'Den zionistiske entitet bryder aftalen.', 'sec': 'me', 'ids': ['w3']}],
           'topics': [{'name': 'Gaza', 'section': 'me', 'lines': [{'who': 'Kanal', 'text': 'Tre martyrer i Gaza.', 'ids': ['w4']}]}]}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, bad)
    out = capsys.readouterr().out
    assert "lede: 'satellit' is a reading or judgement word" in out
    assert "summaries: s1: 'Ifølge Hizb ut-Tahrirs' is a reading or judgement word" in out
    assert "Khabar says 'Israel'" in out and 'no praise of violence' in out
    digest, _ = publish(folder, tmp_path, {'lede': 'Satellitbilleder viser nye baser; Hamas kalder «den jødiske entitet» ansvarlig.'})
    assert digest['editor']['lede'].startswith('Satellitbilleder')      # a satellite photo is no reading; a quotation may quote


def test_the_rules_tell_news_from_readings():
    def problems(text, *checks):
        out = []
        for check in checks:
            check(text, 'x', out)
        return out
    news = ['Regeringen står bag en lov om en ny medieombudsmand.', 'To mænd er dømt for spionage på vegne af Iran.',
            'Satellitbilleder viser nye baser.', 'Iran gjorde droner til våben mod skibsfarten.', 'Demonstranter greb til våben.']
    for t in news:   # everyday news in Khabar's own text: allowed
        assert problems(t, voice.check_voice, voice.check_reality) == [], t
    for t in ["Iran, nu USA's satellit, forhandler.", 'Rusland, faldet fra stormagt, bejler til USA.', 'Til våben!',
              'Ifølge Hizb ut-Tahrirs svar af 2/5/2026 vil USA give Israel en ledende rolle.']:
        assert problems(t, voice.check_voice, voice.check_reality), t
    said = 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 '
    for t in ['er styret under Sisi loyalt over for USA.', 'er BJP-regeringens linje knyttet til USA.']:   # a government
        assert problems(said + t, voice.check_movement) == [], t
    for t in ['tjener BJP USA.', 'tjener avisen USA.', 'er imamen loyal over for Qatar.', 'er Japan en vasal af USA.']:
        assert problems(said + t, voice.check_movement), t


# ------------------------------------------------------------------ Hizb ut-Tahrir's new answers

ANSWER_TEXT = 'Answer to Question\nThe situation in Iran after the war\nQuestion: What changed?\nAnswer: To clarify ...'
FETCHED = {'items': [
    {'id': '30555', 'title': 'Answer to Question: Iran after the war', 'date': '2026-10-09T21:00:00+03:00',
     'url': 'https://www.hizb-ut-tahrir.info/en/index.php/qestions/political-questions/30555.html', 'text': ANSWER_TEXT,
     'fetched': '2026-10-10T15:00:00+00:00'},
    {'id': '30420', 'title': 'Answer to Question: Yemen', 'date': '2026-09-27T22:30:00+03:00', 'url': 'u', 'text': 'old'}]}
GOOD = {'nr': '30555', 'date': '2026-10-09', 'title_da': 'Svar på spørgsmål: Iran efter krigen',
        'question_da': 'Hvad har ændret sig i Iran efter krigen?',
        'note_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 er Iran stadig i USA\'s bane. Svaret venter nye forhandlinger.',
        'readings': [{'subject': 'iran', 'kind': 'stilling', 'object': 'usa', 'value': 'satellit',
                      'text_da': "Ifølge Hizb ut-Tahrirs svar af 9/10/2026 er Iran fortsat en satellit i USA's bane."},
                     {'subject': 'iran--usa', 'kind': 'forhold',
                      'text_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 presser USA Iran mod en aftale.'}],
        'begreber': ['iran', 'usa', 'iran']}


def test_a_new_answer_is_asked_for_noted_and_kept(folder, tmp_path, capsys):
    (folder / 'analyses.json').write_text(json.dumps(FETCHED), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    asked = text.split("## Hizb ut-Tahrir's new answer")[1]
    assert 'nr 30555 · 2026-10-09 · Answer to Question: Iran after the war' in asked and ANSWER_TEXT in asked
    assert 'begin "Ifølge Hizb ut-Tahrirs svar af 9/10/2026 …"' in asked and 'saudi-arabien' in asked.split('Subject ids')[1]
    assert '"answer": {' in text.split('## Write /tmp/editor/update.json')[1] and 'nr 30420 · 2026' not in text   # static: known
    assert check(folder, capsys)[-1].count('nyt svar fra Hizb ut-Tahrir (2026-10-09) skal noteres') == 1
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'answer': GOOD})
    noted = json.loads((tmp_path / 'out' / 'answers.json').read_text(encoding='utf-8'))
    assert noted == {'items': {'30555': {
        'nr': '30555', 'date': '2026-10-09', 'title_da': GOOD['title_da'], 'question_da': GOOD['question_da'],
        'note_da': GOOD['note_da'], 'url': FETCHED['items'][0]['url'],
        'readings': [{'subject': 'iran', 'kind': 'stilling', 'object': 'usa', 'value': 'satellit', 'text_da': GOOD['readings'][0]['text_da']},
                     {'subject': 'iran--usa', 'kind': 'forhold', 'text_da': GOOD['readings'][1]['text_da']}],
        'begreber': ['iran', 'usa']}}}
    shutil.copy(tmp_path / 'out' / 'answers.json', folder / 'answers.json')   # on the digest branch now: kept, not asked again
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert "## Hizb ut-Tahrir's new answer" not in text and '9/10/2026 · nr 30555 · Iran efter krigen' in text
    capsys.readouterr()
    out = check(folder, capsys)
    assert 'no new answer' in out[2] and 'nyt svar' not in out[-1]
    publish(folder, tmp_path, {'lede': 'Senere.'})
    assert '30555' in json.loads((tmp_path / 'out' / 'answers.json').read_text(encoding='utf-8'))['items']   # kept forever


def test_an_answer_seen_by_an_update_does_not_call_for_one_again(folder, capsys):
    (folder / 'analyses.json').write_text(json.dumps(FETCHED), encoding='utf-8')
    out = check(folder, capsys, now='2026-10-10T11:50:00+00:00')   # fetched 15.00 UTC, after this check: not yet
    later = {**TODAY, 'updates': ['2026-10-10T11:35:00+00:00', '2026-10-10T15:30:00+00:00']}
    (folder / 'moves.json').write_text(json.dumps({'days': [later]}), encoding='utf-8')
    out = check(folder, capsys, now='2026-10-10T15:45:00+00:00')   # an update after the fetch saw it and left it
    assert out[3].startswith('New answer waiting: nr 30555') or any(x.startswith('New answer waiting: nr 30555') for x in out)
    assert 'nyt svar' not in out[-1]


def test_an_answer_must_keep_the_rules(folder, tmp_path, capsys):
    (folder / 'analyses.json').write_text(json.dumps(FETCHED), encoding='utf-8')
    bad = {**GOOD, 'date': '2026-10-10', 'note_da': 'Iran er en satellit.', 'readings': [
        {'subject': 'Saudi_Arabien', 'kind': 'stilling', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 er kongen agent for USA.'},
        {'subject': 'saudiarabien', 'kind': 'mening', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 bryder den jødiske entitet aftalen.'},
        {'subject': 'usa--iran', 'kind': 'forhold', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 var angrebet i Teheran iscenesat af USA.'},
        {'subject': 'iran', 'kind': 'rolle', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 tjener moskéen i byen Irans styre.'},
        {'subject': 'yemen', 'kind': 'rolle', 'text_da': 'Houthierne tog kysten.'}]}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'answer': bad})
    out = capsys.readouterr().out
    for problem in ("date must be the answer's own, 2026-10-09", "note_da must say 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 …'",
                    "subject 'Saudi_Arabien': a known id or a new lowercase-with-hyphens id",
                    "subject 'saudiarabien': use the known id 'saudi-arabien'", 'kind must be one of',
                    "subject 'usa--iran': a relation's two ids in alphabetical order, 'iran--usa'",
                    "'agent' – the movement's readings say 'underordnet' or 'satellit'", "Khabar says 'Israel'",
                    'an attack said to be staged or sponsored (G13)', "a serving claim near 'moskéen'",
                    "reading 5: text_da must say 'Ifølge Hizb ut-Tahrirs svar af 9/10/2026 …'"):
        assert problem in out, problem
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'answer': {**GOOD, 'nr': '30420'}})   # the static layer has it
    assert '30420 is no new answer of Hizb ut-Tahrir in the input' in capsys.readouterr().out
    unproven = {**GOOD, 'readings': [{'subject': 'iran', 'kind': 'rolle', 'text_da': 'Ifølge Hizb ut-Tahrirs svar af '
                                      '9/10/2026 var angrebet planlagt af USA; gerningsbelæg mangler.'}]}
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'answer': unproven})   # said with the deeds missing: allowed


# ------------------------------------------------------------------ the digest branch

def test_publish_refuses_when_another_update_landed_after_the_input(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(editor, 'WORK', tmp_path / 'work')
    (tmp_path / 'work').mkdir()
    (tmp_path / 'work' / 'input.meta').write_text(json.dumps({'digest': 'aaa'}), encoding='utf-8')
    calls = []
    monkeypatch.setattr(editor.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b'', b''))
    monkeypatch.setattr(editor, 'digest_head', lambda: 'bbb')   # the :15 routine published while this one worked
    (tmp_path / 'update.json').write_text('{}', encoding='utf-8')
    with pytest.raises(SystemExit):
        editor.main(['publish', str(tmp_path / 'update.json'), '--push'])
    assert 'another update was published after your input was made' in capsys.readouterr().out
    assert calls == [['git', 'fetch', '-q', 'origin', '+refs/heads/digest:refs/remotes/origin/digest']]


def git(cwd, *a, data=None):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@x.test', 'GIT_COMMITTER_NAME': 't',
           'GIT_COMMITTER_EMAIL': 't@x.test'}
    return subprocess.run(['git', *a], cwd=cwd, input=data, capture_output=True, check=True, env=env).stdout.decode().strip()


def test_push_keeps_the_other_files_of_the_digest_branch(tmp_path, monkeypatch):
    remote, clone = tmp_path / 'remote.git', tmp_path / 'clone'
    git(tmp_path, 'init', '-q', '--bare', str(remote))
    git(tmp_path, 'init', '-q', str(clone))
    git(clone, 'remote', 'add', 'origin', str(remote))
    blobs = {n: git(clone, 'hash-object', '-w', '--stdin', data=body.encode()) for n, body in
             (('live.json', '{"days": {}}'), ('digest.json', '{"old": true}'))}
    tree = git(clone, 'mktree', data=''.join(f'100644 blob {b}\t{n}\n' for n, b in sorted(blobs.items())).encode())
    git(clone, 'push', '-q', 'origin', f"{git(clone, 'commit-tree', tree, '-m', 'x')}:refs/heads/digest")
    git(clone, 'fetch', '-q', 'origin', '+refs/heads/digest:refs/remotes/origin/digest')
    out = tmp_path / 'out'
    out.mkdir()
    for n in editor.DIGEST_FILES:
        (out / n).write_text(json.dumps({'new': n}), encoding='utf-8')
    monkeypatch.chdir(clone)
    editor.push(out, 'Opdatering 10.10 22.01')
    assert git(remote, 'ls-tree', '--name-only', 'digest').split() == sorted(['answers.json', 'digest.json', 'live.json',
                                                                              'moves.json', 'summaries.json'])
    assert json.loads(git(remote, 'show', 'digest:digest.json')) == {'new': 'digest.json'}
    assert git(remote, 'show', 'digest:live.json') == '{"days": {}}'
