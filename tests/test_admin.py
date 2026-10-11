import hashlib
import hmac
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radar import admin  # noqa: E402

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
KEY = 'abcd-efgh-ijkl-mnop'
ITEMS = {'s1': {'title': 'AP hub page', 'source': 'AP', 'link': 'https://apnews.com/hub/x'}}


def signed(**m):
    m.setdefault('at', str(int(NOW.timestamp() * 1000)))
    m['sig'] = hmac.new(KEY.encode(), admin.signed_text(m).encode(), hashlib.sha256).hexdigest()
    return {'kind': 'admin', **m}


def run(msgs, state=None, key=KEY):
    state = state or {'removed': [], 'moved': {}}
    return admin.apply(state, msgs, ITEMS, key, NOW, lambda it: it['title']), state


def test_a_signed_removal_is_remembered_with_its_reason():
    n, st = run([signed(act='hide', id='s1', why='noise', sec='')])
    assert n == 1 and st['removed'][0]['id'] == 's1' and st['removed'][0]['why'] == 'noise'
    assert st['removed'][0]['t'] == 'AP hub page'


def test_unsigned_wrong_key_old_or_odd_messages_do_nothing():
    bad_sig = {**signed(act='hide', id='s1', why='noise', sec=''), 'sig': '0' * 64}
    old = signed(act='hide', id='s1', why='noise', sec='', at=str(int((NOW - timedelta(days=4)).timestamp() * 1000)))
    odd = signed(act='hide', id='s1', why='because', sec='')
    unknown = signed(act='hide', id='nope', why='noise', sec='')
    n, st = run([bad_sig, old, odd, unknown, {'kind': 'admin', 'act': 'hide', 'id': 's1'}])
    assert n == 0 and st['removed'] == []
    n, st = run([signed(act='hide', id='s1', why='noise', sec='')], key='')   # no ADMIN_KEY set: nothing counts
    assert n == 0


def test_move_and_undo():
    n, st = run([signed(act='move', id='s1', why='', sec='dk')])
    assert st['moved'] == {'s1': 'dk'}
    n, st = run([signed(act='hide', id='s1', why='dup', sec=''), signed(act='undo', id='s1', why='', sec='')], st)
    assert st['removed'] == [] and st['moved'] == {}


def test_prune_forgets_old_removals():
    st = {'removed': [{'id': 'a', 'at': (NOW - timedelta(days=40)).isoformat()},
                      {'id': 'b', 'at': (NOW - timedelta(days=2)).isoformat()}], 'moved': {}}
    assert [r['id'] for r in admin.prune(st, NOW, 30)['removed']] == ['b']


def test_the_owner_picks_the_front_page_quote():
    n, st = run([signed(act='quote', id='0a1b2c3d', why='', sec='')])
    assert n == 1 and st['quote']['key'] == '0a1b2c3d'
    n, st = run([signed(act='quote', id='not-a-key', why='', sec='')], st)
    assert n == 0 and st['quote']['key'] == '0a1b2c3d'
    n, st = run([signed(act='quote', id='', why='', sec='')], st)   # back to the editor's choice
    assert n == 1 and 'quote' not in st
