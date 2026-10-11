"""The owner's statistics: what the relay messages become, counted per Danish day, and the sealed file."""
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import feedback, stats  # noqa: E402

NOW = datetime(2026, 10, 11, 21, 0, tzinfo=timezone.utc)
UNIX = lambda y, mo, d, h, mi=0: int(datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp())  # noqa: E731


def visit(at, **kw):
    return {'kind': 'visit', 'app': True, 'first': False, 'os': 'ios', 'tz': 'Europe/Copenhagen', 'lang': 'da', 'via': 'direct', 'at': at, **kw}


def test_openings_land_in_their_danish_day_and_hour():
    s = stats.add({}, [visit(UNIX(2026, 10, 11, 20, 30)),                         # 22:30 in Copenhagen (summer time)
                       visit(UNIX(2026, 10, 11, 22, 30), app=False, os='android', first=True, lang='ar', via='whatsapp'),   # 00:30 next day
                       visit(UNIX(2026, 10, 11, 6, 0), tz='Europe/Stockholm', via='push')], phones=7, now=NOW)
    d, nxt = s['days']['2026-10-11'], s['days']['2026-10-12']
    assert (d['opens'], d['new'], d['app'], d['ios'], d['h'][22], d['h'][8]) == (2, 0, 2, 2, 1, 1)
    assert d['tz'] == {'Europe/Copenhagen': 1, 'Europe/Stockholm': 1} and d['via'] == {'direct': 1, 'push': 1}
    assert (nxt['opens'], nxt['new'], nxt['app'], nxt['android'], nxt['h'][0], nxt['lang'], nxt['via']) == (1, 1, 0, 1, 1, {'ar': 1}, {'whatsapp': 1})
    assert s['phones'] == 7 and s['since'] == '2026-10-11'


def test_time_in_the_app_tabs_and_most_read():
    at = UNIX(2026, 10, 11, 12)
    s = stats.add({}, [{'kind': 'leave', 'secs': 120, 'opened': 3, 'tabs': {'home': 2, 'latest': 1}, 'at': at},
                       {'kind': 'leave', 'secs': 60, 'opened': 0, 'tabs': {'home': 1}, 'at': at},
                       {'kind': 'read', 'id': 'a1', 'title': 'Gaza', 'at': at},
                       {'kind': 'read', 'id': 'a1', 'title': 'Gaza', 'at': at},
                       {'kind': 'share', 'id': 'a1', 'title': 'Gaza', 'at': at}], phones=0, now=NOW)
    d = s['days']['2026-10-11']
    assert (d['secs'], d['stays'], d['opened'], d['tabs']) == (180, 2, 3, {'home': 3, 'latest': 1})
    assert d['top'] == {'a1': ['Gaza', 2, 1]}


def test_old_days_go_and_old_titles_first():
    s = {'days': {'2026-05-01': stats.empty_day(), '2026-09-20': {**stats.empty_day(), 'top': {'x': ['t', 1, 0]}},
                  '2026-10-10': {**stats.empty_day(), 'top': {'y': ['t', 1, 0]}}}}
    s = stats.add(s, [], phones=0, now=NOW)
    assert '2026-05-01' not in s['days']                                   # past 120 days
    assert 'top' not in s['days']['2026-09-20'] and s['days']['2026-10-10']['top']   # titles only 14 days back


def test_the_public_relay_cannot_flood_it():
    many = [visit(UNIX(2026, 10, 11, 12), tz=f'Europe/Z{n}') for n in range(stats.MAX_PER_RUN + 50)]
    d = stats.add({}, many, phones=0, now=NOW)['days']['2026-10-11']
    assert d['opens'] == stats.MAX_PER_RUN and len(d['tz']) == stats.MAX_KEYS


def test_relay_messages_are_checked(monkeypatch):
    lines = [json.dumps({'event': 'message', 'id': str(n), 'time': 1760000000, 'message': json.dumps(b)}) for n, b in enumerate([
        {'kind': 'visit', 'app': 1, 'os': 'ios', 'tz': 'Asia/Gaza', 'lang': 'AR', 'via': 'whatsapp', 'first': 1},
        {'kind': 'visit', 'os': 'windows', 'tz': '<script>', 'lang': 'dansk', 'via': 'evil'},
        {'kind': 'leave', 'secs': 99999, 'opened': 'x', 'tabs': {'home': 3, 'hack': 9}},
        {'kind': 'read', 'id': 'a1', 'title': 'Gaza', 'me': 1}])]

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv('FEEDBACK_TOPIC', 'topic')
    monkeypatch.setattr(feedback.urllib.request, 'urlopen', lambda *a, **k: Resp('\n'.join(lines).encode()))
    out, last = feedback.pull(None)
    good, bad, leave, read = out
    assert good == {'kind': 'visit', 'app': True, 'first': True, 'os': 'ios', 'tz': 'Asia/Gaza', 'lang': 'ar', 'via': 'whatsapp', 'at': 1760000000}
    assert (bad['os'], bad['tz'], bad['lang'], bad['via'], bad['app']) == ('other', '', '', 'direct', False)
    assert (leave['secs'], leave['opened'], leave['tabs']) == (4 * 3600, 0, {'home': 3})
    assert read['me'] is True and last == '3'


def test_sealed_so_only_the_admin_code_opens_it(tmp_path):
    pytest.importorskip('cryptography')
    path = tmp_path / 'stats.enc'
    stats.update(path, 'abcd-1234', [visit(UNIX(2026, 10, 11, 12))], 3, NOW)
    stats.update(path, 'abcd-1234', [visit(UNIX(2026, 10, 11, 13))], 4, NOW)
    text = path.read_text()
    assert 'opens' not in text and stats.unseal(text, ' ABCD-1234 ')['days']['2026-10-11']['opens'] == 2
    with pytest.raises(Exception):
        stats.unseal(text, 'another-code')
    assert stats.update(path, '', [], 0, NOW) is None   # no admin code: nothing counted


def test_reads_what_the_owners_app_makes():
    # made in the browser with WebCrypto (AES-GCM, the key from 'Test-Key ', iv 1..12): the app's way and the radar's agree
    pytest.importorskip('cryptography')
    assert stats.unseal('AQIDBAUGBwgJCgsMoIfX0pqVD7xZthrW3HUOIwBexODl3S7rJ5NHMlT6YaDuH/K7VA==', 'test-key') == {'ok': 'æøå', 'n': 1}
