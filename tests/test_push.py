"""Phones that sign up by themselves: which addresses count, the daily cap, switching off."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import push  # noqa: E402

KEYS = {'p256dh': 'BOq' + 'x' * 80, 'auth': 'a' * 22}


def sub(n, host='web.push.apple.com'):
    return {'endpoint': f'https://{host}/QG{n}', 'keys': KEYS}


def test_only_real_push_services_count():
    assert push.valid(sub(1)) and push.valid(sub(2, 'fcm.googleapis.com'))
    assert push.valid(sub(3, 'updates.push.services.mozilla.com'))
    assert not push.valid(sub(4, 'evil.example.com'))
    assert not push.valid({'endpoint': 'http://web.push.apple.com/x', 'keys': KEYS})
    assert not push.valid({'endpoint': 'https://web.push.apple.com/x', 'keys': {'auth': 'a'}})


def test_sign_up_caps_and_switch_off():
    signals = [{'kind': 'sub', 'sub': sub(n)} for n in range(5)] + [{'kind': 'sub', 'sub': sub(0)}]
    phones = push.sign_up([], signals, 'now', today=push.NEW_PER_DAY - 3)
    assert [p['endpoint'][-3:] for p in phones] == ['QG0', 'QG1', 'QG2']   # 3 left today; no doubles
    phones = push.sign_up(phones, [{'kind': 'unsub', 'sub': sub(1)}], 'later', today=0)
    assert [p['endpoint'][-3:] for p in phones] == ['QG0', 'QG2']


def test_everyone_merges_the_old_secret(monkeypatch):
    monkeypatch.setenv('PUSH_SUBS', '[{"endpoint": "https://web.push.apple.com/QG0", "keys": {}}]')
    got = push.everyone([{**sub(0), 'at': 'x'}, {**sub(7), 'at': 'x'}])
    assert [s['endpoint'][-3:] for s in got] == ['QG0', 'QG7'] and 'at' not in got[1]
