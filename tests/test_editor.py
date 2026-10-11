"""The editor's tools: the recap of the day, which wire lines it is given, and what publishing writes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import editor  # noqa: E402

NOW = '2026-10-10T20:01:00+00:00'   # 22.01 Danish summer time


def wire(i, hhmm, text):
    return {'i': i, 't': f'نص {i}', 'tr': text, 'p': f'2026-10-10T{hhmm}:00+00:00', 'u': f'https://t.me/ajanews/{i}', 'k': 'w'}


TODAY = {'date': '2026-10-10', 'title': 'Politiske nyheder – 10. oktober 2026', 'created': '2026-10-10T11:35:00+00:00',
         'updates': ['2026-10-10T11:35:00+00:00'], 'ids': ['w1'], 'topics': [
             {'name': 'Ukraine', 'section': 'world', 'lines': [
                 {'who': 'Kyivs borgmester', 'text': 'Fire såret.', 'link': 'https://t.me/ajanews/w1', 'source': 'Al Jazeera',
                  'at': '2026-10-10T08:00:00+00:00', 'added': '2026-10-10T11:35:00+00:00', 'id': 'w1', 'kind': 'w'}]}]}


@pytest.fixture
def folder(tmp_path, monkeypatch):
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
    assert digest['editor'] == {'created': '2026-10-10T20:01:00+00:00', 'lede': 'Dagen kort.', 'picks': [{'id': 's3', 'why': 'Stormagter'}],
                                'moves': [{'id': 's4', 'sec': 'world'}],
                                'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world',
                                            'link': 'https://t.me/ajanews/w3'}]}
    assert digest['push']['title'] == 'Khabar · dagens resumé, 10. oktober'   # the evening update tells the phones
    assert moves['days'][0]['date'] == '2026-10-10' and 'editor' not in moves['days'][0]


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
                    "picks: unknown story id 'nope'", 'moves:'):
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
