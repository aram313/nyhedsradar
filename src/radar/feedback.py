"""Collect the 'Kopiér' and 'Ikke relevant' taps from the phone.

The app posts each tap as a tiny message to a private ntfy.sh topic (a free message relay);
every radar run picks up what arrived since last time. Only public headlines travel this way."""
import json
import os
import urllib.request


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
        if body.get('kind') in ('up', 'down') and body.get('title'):
            out.append({'id': str(body.get('id', ''))[:32], 'kind': body['kind'], 'title': str(body['title'])[:300],
                        'summary': str(body.get('summary', ''))[:300], 'at': msg.get('time')})
    return out, last
