"""Collect what the owner shares, copies and opens in the app (silent signals, no buttons).

The app posts each tap as a tiny message to a private ntfy.sh topic (a free message relay);
every radar run picks up what arrived since last time. Only public headlines travel this way – and a phone's
push address when its owner switches notifications on or off (see push.py), and a bare 'the app was opened'
for the owner's statistics (see stats.py)."""
import json
import os
import re
import urllib.request

ZONE = re.compile(r'^[A-Za-z]+(?:/[A-Za-z0-9_+\-]+){0,2}$')
VIAS = ('push', 'whatsapp', 'facebook', 'google', 'sms', 'web', 'direct', 'resume')
TABS = ('home', 'dk', 'me', 'world', 'threads', 'latest', 'search')


def num(x, top):
    try:
        return max(0, min(top, int(x)))
    except (TypeError, ValueError):
        return 0


def pull(since):
    topic = os.environ.get('FEEDBACK_TOPIC', '').strip()
    if not topic:
        return [], since
    url = f'https://ntfy.sh/{topic}/json?poll=1&since={since or "24h"}'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Nyhedsradar'}), timeout=20) as r:
            lines = r.read().decode('utf-8').splitlines()
    except Exception as e:  # feedback is a bonus; never stop the radar over it
        print('feedback: could not read relay:', e)
        return [], since
    out, last = [], since
    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get('event') != 'message':
            continue
        last = msg['id']
        try:
            body = json.loads(msg.get('message', ''))
        except json.JSONDecodeError:
            continue
        if body.get('kind') in ('sub', 'unsub') and isinstance(body.get('sub'), dict):   # a phone switching on/off
            want = body.get('want')   # the kinds the phone asked for (the app's three switches); missing: as before
            out.append({'kind': body['kind'], 'sub': body['sub'], 'at': msg.get('time'),
                        **({'want': [k for k in want if k in ('top', 'digest', 'svar')]} if isinstance(want, list) else {})})
        elif body.get('kind') == 'admin':   # the owner's hand; admin.py checks the signature and each act's form
            # a comment's words and what its element showed are longer than an action's codes (18/10); a field cut short
            # breaks the signature, so a too long one is refused, not cut
            out.append({'kind': 'admin', **{k: str(body.get(k, ''))[:n] for k, n in
                                            (('act', 80), ('id', 160), ('why', 1000), ('sec', 500), ('at', 80), ('sig', 80))}})
        elif body.get('kind') == 'visit':   # the app was opened: counted for the owner's statistics (stats.py)
            tz, lang = str(body.get('tz', ''))[:40], str(body.get('lang', ''))[:8].lower()
            out.append({'kind': 'visit', 'app': body.get('app') in (1, True), 'first': body.get('first') in (1, True),
                        'os': body.get('os') if body.get('os') in ('ios', 'android', 'other') else 'other',
                        'tz': tz if ZONE.match(tz) else '', 'lang': lang if re.fullmatch(r'[a-z]{2,3}', lang) else '',
                        'via': body.get('via') if body.get('via') in VIAS else 'direct', 'at': msg.get('time')})
        elif body.get('kind') == 'leave':   # the app went to the background: how long, which tabs (stats.py)
            tabs = body.get('tabs') if isinstance(body.get('tabs'), dict) else {}
            out.append({'kind': 'leave', 'secs': num(body.get('secs'), 4 * 3600), 'opened': num(body.get('opened'), 200),
                        'tabs': {k: num(v, 100) for k, v in tabs.items() if k in TABS}, 'at': msg.get('time')})
        elif body.get('kind') in ('up', 'share', 'read') and body.get('title'):
            out.append({'id': str(body.get('id', ''))[:32], 'kind': body['kind'], 'title': str(body['title'])[:300],
                        'summary': str(body.get('summary', ''))[:300], 'at': msg.get('time'),
                        'me': body.get('me') in (1, True)})   # the owner's own: teaches, but is not counted
    return out, last
