"""The owner's hand on the radar: from the app, a long press on a story removes it or moves it to another section.

The app signs each action with the owner's admin code (HMAC-SHA256); the radar checks it against the ADMIN_KEY
secret, so a message posted to the public relay by anyone else does nothing. A removal is remembered in
state/removed.json: the story leaves the app for everyone, stories very like an 'irrelevant' or 'not news' one
stay out too, near ones rank lower, and the editor reads the list so it learns the owner's taste. Holding the front
page's quote picks which statement it shows (data.json `owner.quote`, a short key the app computes from who and text)."""
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone

WHYS = {'irrelevant': 'irrelevant', 'noise': 'ikke en nyhed', 'dup': 'dublet'}
SECS = ('dk', 'me', 'world')
LEARN = ('irrelevant', 'noise')   # what teaches 'less like this'; a duplicate says nothing about taste


def signed_text(m):
    return f"{m.get('act', '')}|{m.get('id', '')}|{m.get('why', '')}|{m.get('sec', '')}|{m.get('at', '')}"


def valid(m, key, now):
    """A real action from the owner: signed with the admin key, fresh, and well formed."""
    if not key or not isinstance(m.get('sig'), str):
        return False
    good = hmac.new(key.encode(), signed_text(m).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good, m['sig'].lower()):
        return False
    try:
        at = datetime.fromtimestamp(int(m['at']) / 1000, timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False
    if not now - timedelta(days=3) <= at <= now + timedelta(minutes=10):
        return False
    if m.get('act') == 'hide':
        return m.get('why') in WHYS
    if m.get('act') == 'move':
        return m.get('sec') in SECS
    if m.get('act') == 'quote':   # the front page's quote: a quote's short key, or '' for the editor's own choice
        return bool(re.fullmatch(r'(?:[0-9a-f]{8})?', m.get('id', '')))
    return m.get('act') == 'undo'


def apply(state, msgs, items, key, now, text):
    """Fold the owner's new actions into state {removed: [...], moved: {id: sec}}; returns how many counted.
    `text(item)` gives the words the radar learns from."""
    done = 0
    for m in msgs:
        if not valid(m, key, now):
            continue
        sid, it = m['id'], items.get(m['id'])
        if m['act'] == 'quote':
            if sid:
                state['quote'] = {'key': sid, 'at': now.isoformat()}
            else:
                state.pop('quote', None)
        elif m['act'] == 'undo':
            state['removed'] = [r for r in state['removed'] if r['id'] != sid]
            state['moved'].pop(sid, None)
        elif m['act'] == 'move':
            state['moved'][sid] = m['sec']
        elif it and not any(r['id'] == sid for r in state['removed']):
            state['removed'].append({'id': sid, 'why': m['why'], 'at': now.isoformat(), 't': text(it),
                                     'title': it['title'], 'source': it['source'], 'link': it['link']})
        else:
            continue
        done += 1
    return done


def prune(state, now, days):
    state['removed'] = [r for r in state['removed'] if datetime.fromisoformat(r['at']) >= now - timedelta(days=days)]
    return state


def load(path):
    try:
        st = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        st = {}
    out = {'removed': st.get('removed') or [], 'moved': st.get('moved') or {}}
    if st.get('quote'):
        out['quote'] = st['quote']
    return out
