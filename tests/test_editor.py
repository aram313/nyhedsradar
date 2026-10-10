"""The editor's tools: which wire lines an edition must cover, and what publishing writes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import editor  # noqa: E402

NOW = '2026-10-10T20:01:00+00:00'   # 22.01 Danish summer time


def wire(i, hhmm, text):
    return {'i': i, 't': f'نص {i}', 'tr': text, 'p': f'2026-10-10T{hhmm}:00+00:00', 'u': f'https://t.me/ajanews/{i}', 'k': 'w'}


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(editor, 'WORK', tmp_path / 'work')
    d = tmp_path / 'in'
    d.mkdir()
    (d / 'data.json').write_text(json.dumps({'items': [
        {'id': 's1', 'title': 'Regeringen strammer reglerne', 'summary': '', 'link': 'https://dr.test/1', 'source': 'DR',
         'sec': 'dk', 'rank': 90, 'confirmed': 3, 'published': '2026-10-10T12:00:00+00:00', 'found': '2026-10-10T12:01:00+00:00'},
        {'id': 's3', 'title': 'Already in the 13.35 edition', 'summary': '', 'link': 'https://x.test/3', 'source': 'BBC',
         'sec': 'world', 'rank': 95, 'published': '2026-10-10T09:00:00+00:00', 'found': '2026-10-10T09:01:00+00:00'},
        {'id': 's2', 'title': 'Old story', 'summary': '', 'link': 'https://x.test/2', 'source': 'BBC', 'sec': 'world',
         'rank': 99, 'published': '2026-10-09T09:00:00+00:00', 'found': '2026-10-09T09:01:00+00:00'}]}), encoding='utf-8')
    (d / 'lines.json').write_text(json.dumps({'items': [
        wire('w1', '08:00', 'covered this morning'), wire('w2', '11:32', 'arrived after the last edition was made'),
        wire('w3', '19:00', 'Kremlin: talks go on'), wire('w4', '19:05', 'Kremlin: talks continue'),
        {'i': 'h1', 't': 'Trump: x', 'p': '2026-10-10T19:00:00+00:00', 'u': 'https://x.test/h', 'k': 'h'}]}), encoding='utf-8')
    earlier = {'created': '2026-10-10T11:35:00+00:00', 'until': '2026-10-10T11:35:00+00:00', 'ids': ['w1'], 'topics': []}
    (d / 'moves.json').write_text(json.dumps({'briefs': [earlier]}), encoding='utf-8')
    return d


def test_input_lists_every_uncovered_line(folder):
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert '[w2]' in text and '[w3]' in text and '[w4]' in text and '[w1]' not in text and '[h1]' not in text
    assert '[s1]' in text and '[s2]' not in text and '[s3]' not in text   # only what came after the last edition
    assert 'aften' in text


def test_old_editions_without_ids_cover_up_to_their_end():
    lines = {'items': [wire('a', '10:00', ''), wire('b', '12:00', '')]}
    assert [v['i'] for v in editor.uncovered(lines, [{'until': '2026-10-10T11:00:00+00:00'}])] == ['b']


def test_publish(folder, tmp_path, capsys):
    draft = {'intro': 'Dagens vigtigste.', 'topics': [
        {'name': 'Statsborgerskab', 'section': 'dk', 'stories': [{'id': 's1', 'headline': 'Strammere regler', 'text': 'To sætninger.'}]},
        {'name': 'Ukraine', 'section': 'world', 'lines': [{'ids': ['w3', 'w4'], 'who': 'Kreml', 'text': 'Samtalerne fortsætter.'}]}]}
    path = tmp_path / 'edition.json'
    path.write_text(json.dumps(draft), encoding='utf-8')
    with pytest.raises(SystemExit):   # the 11.32 line that came in late must not be forgotten
        editor.main(['publish', str(path), '--dir', str(folder), '--now', NOW])
    assert 'w2' in capsys.readouterr().out

    draft['topics'][1]['lines'].append({'ids': ['w2'], 'who': 'Al Jazeera', 'text': 'En linje.'})
    path.write_text(json.dumps(draft), encoding='utf-8')
    editor.main(['publish', str(path), '--dir', str(folder), '--now', NOW, '--out', str(tmp_path / 'out')])
    digest = json.loads((tmp_path / 'out' / 'digest.json').read_text(encoding='utf-8'))
    moves = json.loads((tmp_path / 'out' / 'moves.json').read_text(encoding='utf-8'))
    assert digest['period'] == 'aften' and digest['title'] == 'Politiske nyheder – 10. oktober 2026'
    assert digest['items'][0]['link'] == 'https://dr.test/1' and digest['items'][0]['source'] == 'DR'
    assert digest['ids'] == ['w2', 'w3', 'w4'] and digest['from'] == '2026-10-10T11:32:00+00:00'
    assert digest['topics'][1]['lines'][0]['link'] == 'https://t.me/ajanews/w3'
    assert digest['whatsapp'].startswith('*Dagens overblik – aften, lørdag 10. oktober 2026*')
    assert '1. *Strammere regler*\nTo sætninger.\nhttps://dr.test/1' in digest['whatsapp']
    assert digest['lines_whatsapp'] == ('Politiske nyheder – 10. oktober 2026\n\nUkraine\n\n- Kreml: Samtalerne fortsætter.'
                                        '\n\n- Al Jazeera: En linje.')
    assert [e['created'] for e in moves['briefs']] == [digest['created'], '2026-10-10T11:35:00+00:00']
    assert moves['briefs'][1] == {'created': '2026-10-10T11:35:00+00:00', 'until': '2026-10-10T11:35:00+00:00',
                                  'ids': ['w1'], 'topics': []}   # earlier editions are never changed
    assert 'whatsapp' not in moves['briefs'][0]


def test_dates():
    t = editor.ts
    assert editor.span_da(t('2026-10-09T20:30:00+00:00'), t('2026-10-10T05:00:00+00:00')) == '9. og 10. oktober 2026'
    assert editor.span_da(t('2026-10-31T20:00:00+00:00'), t('2026-11-01T06:00:00+00:00')) == '31. oktober og 1. november 2026'
    assert editor.period_of(t('2026-10-10T05:01:00+00:00')) == 'morgen'


def test_window_starts_at_the_last_edition():
    t = editor.ts
    now = t('2026-10-10T13:01:00+00:00')   # 15.01 Danish time
    assert editor.window_start(now, 'eftermiddag', [{'created': '2026-10-10T05:02:00+00:00'}]) == t('2026-10-10T05:02:00+00:00')
    assert editor.window_start(now, 'eftermiddag', []) == t('2026-10-10T05:00:00+00:00')          # 07.00 Danish time
    assert editor.window_start(t('2026-10-10T20:01:00+00:00'), 'aften', []) == t('2026-10-10T13:00:00+00:00')   # 15.00
    old = [{'created': '2026-10-08T20:00:00+00:00'}]          # too old to count: the usual start
    assert editor.window_start(now, 'eftermiddag', old) == t('2026-10-10T05:00:00+00:00')
