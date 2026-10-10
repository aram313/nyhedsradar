"""The editor's tools: the day's overview, which wire lines an update is given, and what publishing writes."""
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


def test_input_shows_the_day_so_far_and_only_new_material(folder):
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert "Today's overview so far (10. oktober 2026) – 1 lines in 1 topics" in text
    assert '### Ukraine (world)' in text and '[w1] 10.00 · Kyivs borgmester: Fire såret.' in text
    assert '[w2]' in text and '[w3]' in text and '[w4]' in text and '[h1]' not in text
    assert '[s1]' in text and '[s2]' not in text and '[s3]' not in text   # only what came after the last update
    assert 'update.json' in text


def test_publish_adds_to_the_day(folder, tmp_path):
    digest, moves = publish(folder, tmp_path, {
        'topics': [{'name': 'Statsborgerskab', 'section': 'dk', 'lines': [
                       {'who': 'Regeringen', 'text': 'Reglerne for statsborgerskab skal strammes.', 'story': 's1'}]},
                   {'name': 'ukraine ', 'lines': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'ids': ['w3', 'w4']}]}],
        'order': ['Statsborgerskab', 'Ukraine']})
    assert digest['date'] == '2026-10-10' and digest['title'] == 'Politiske nyheder – 10. oktober 2026'
    assert [tp['name'] for tp in digest['topics']] == ['Statsborgerskab', 'Ukraine']
    dk_line = digest['topics'][0]['lines'][0]
    assert dk_line['link'] == 'https://dr.test/1' and dk_line['source'] == 'DR' and dk_line['at'] == '2026-10-10T12:00:00+00:00'
    ukraine = digest['topics'][1]['lines']
    assert [x['who'] for x in ukraine] == ['Kreml', 'Kyivs borgmester']   # the day's topic continued, newest first
    assert ukraine[0]['link'] == 'https://t.me/ajanews/w3' and ukraine[0]['source'] == 'Al Jazeera'
    assert digest['ids'] == ['w1', 'w2', 'w3', 'w4']   # w2 was given and left out: done all the same
    assert digest['updates'] == ['2026-10-10T11:35:00+00:00', '2026-10-10T20:01:00+00:00']
    assert digest['whatsapp'] == ('Politiske nyheder – 10. oktober 2026\n\nStatsborgerskab\n\n- Regeringen: Reglerne for '
                                  'statsborgerskab skal strammes.\n\nUkraine\n\n- Kreml: Samtalerne fortsætter.\n\n'
                                  '- Kyivs borgmester: Fire såret.')
    assert digest['push'] == {'title': 'Khabar · overblik kl. 22',
                              'body': 'Regeringen: Reglerne for statsborgerskab skal strammes.  (+1 mere)'}
    assert moves['days'][0] == {k: v for k, v in digest.items() if k not in ('period', 'whatsapp', 'push')}


def test_publish_refuses_what_does_not_fit(folder, tmp_path, capsys):
    bad = {'topics': [{'name': 'Gaza', 'section': 'gaza', 'lines': [
        {'who': '', 'text': 'Uden afsender.', 'ids': ['w1']},             # w1 was looked at this morning
        {'who': 'Kanal', 'text': 'x' * 300, 'story': 's9'},
        {'who': 'Kreml', 'text': 'To gange.', 'ids': ['w3', 'w3']}]}],
        'order': ['Gaza', 'Sudan'], 'drop': ['nope']}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, bad)
    out = capsys.readouterr().out
    for problem in ("section must be dk, me or world", 'needs who and text', "'w1' is no new wire line", 'is too long',
                    "unknown story id 's9'", 'wire line w3 is used twice', "order: 'Sudan' is no topic of the day",
                    "drop: 'nope' is no line in today's overview"):
        assert problem in out, problem
    many = {'topics': [{'name': 'Ukraine', 'lines': [{'who': 'Kreml', 'text': f'Linje {n}.', 'ids': [f'w{n}']}
                                                     for n in range(2, 5)]}]}
    editor.MAX_NEW, keep = 2, editor.MAX_NEW
    try:
        with pytest.raises(SystemExit):
            publish(folder, tmp_path, many)
    finally:
        editor.MAX_NEW = keep
    assert '3 new lines – at most 2' in capsys.readouterr().out


def test_the_first_update_after_midnight_starts_a_new_day(folder, tmp_path):
    digest, moves = publish(folder, tmp_path, {'topics': [{'name': 'Ukraine', 'section': 'world', 'lines': [
        {'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'ids': ['w3']}]}]}, now='2026-10-11T05:02:00+00:00')
    assert digest['date'] == '2026-10-11' and digest['title'] == 'Politiske nyheder – 11. oktober 2026'
    assert [x['who'] for x in digest['topics'][0]['lines']] == ['Kreml']     # yesterday's line stays in yesterday
    assert [d['date'] for d in moves['days']] == ['2026-10-11', '2026-10-10']
    assert moves['days'][1] == TODAY
    assert digest['push']['title'] == 'Khabar · overblik kl. 7'


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
    now = t('2026-10-10T13:01:00+00:00')   # 15.01 Danish time
    assert editor.window_start(now, 'eftermiddag', ['2026-10-10T05:02:00+00:00']) == t('2026-10-10T05:02:00+00:00')
    assert editor.window_start(now, 'eftermiddag', []) == t('2026-10-10T05:00:00+00:00')          # 07.00 Danish time
    assert editor.window_start(t('2026-10-10T20:01:00+00:00'), 'aften', []) == t('2026-10-10T13:00:00+00:00')   # 15.00
    assert editor.window_start(now, 'eftermiddag', ['2026-10-08T20:00:00+00:00']) == t('2026-10-10T05:00:00+00:00')
    assert editor.period_of(t('2026-10-10T05:01:00+00:00')) == 'morgen'
