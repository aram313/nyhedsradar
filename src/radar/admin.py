"""The owner's hand on the radar: from the app, a long press on a story removes it or moves it to another section.

The app signs each action with the owner's admin code (HMAC-SHA256); the radar checks it against the ADMIN_KEY
secret, so a message posted to the public relay by anyone else does nothing. A removal is remembered in
state/removed.json: the story leaves the app for everyone, stories very like an 'irrelevant' or 'not news' one
stay out too, near ones rank lower, and the editor reads the list so it learns the owner's taste. Holding the front
page's quote picks which statement it shows (data.json `owner.quote`, a short key the app computes from who and text);
holding the main story picks another (`owner.lead`); any story can be raised or lowered (`owner.rank`, the rank moves).

Since 18/10 (the owner: 'Giv mig også et felt hvor jeg kan skrive en kommentar til elementet til redaktørerne … alle
elementer burde kunne holdes nede og få en "kommentar" valgmulighed' – 'giv også en funktion der lader mig edit
overskrifter direkte'): every element he holds can carry a comment to the editors (`note`: the element's reference, his
words and what it showed; kept NOTE_DAYS in `notes`, the editors' input lists the open ones and they answer in
owner.json on the digest branch), and a story's or an event page's headline can be his own (`title`, `owner.titles`:
his words win in the app and in the notifications, and the editors learn from them)."""
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone

WHYS = {'irrelevant': 'irrelevant', 'noise': 'ikke en nyhed', 'dup': 'dublet'}
SECS = ('dk', 'me', 'world')
LEARN = ('irrelevant', 'noise')   # what teaches 'less like this'; a duplicate says nothing about taste
NOTE_TEXT, NOTE_CTX, NOTE_DAYS = 1000, 500, 14   # a comment's words, what the element showed, the days it is kept
TITLE_TEXT, TITLE_DAYS, EVENT_TITLE_DAYS = 200, 4, 30   # an own headline; a story's lasts as long as the editor's would
REF = re.compile(r'[\w:.\-/]{1,160}')        # an element's reference: 'story:<id>', 'ev:<id>:fakta:2', 'kal:<id>', 'oko:…'
TITLE_ID = re.compile(r'[0-9a-f]{16}|ev:[a-z0-9][a-z0-9-]{0,80}')   # a story, or an event page ('ev:<id>')
NOTE_ID = re.compile(r'n\d{10,16}')            # a comment is known by the moment it was written


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
    if m.get('act') == 'lead':    # the front page's main story: a story id, or '' for the automatic choice
        return bool(re.fullmatch(r'(?:[0-9a-f]{16})?', m.get('id', '')))
    if m.get('act') == 'pic':     # a story's picture, or an event page's ('ev:<id>', 19/10): a picture's key, or '' for the automatic
        return bool(TITLE_ID.fullmatch(m.get('id', ''))) and bool(re.fullmatch(r'(?:[0-9a-f]{16})?', m.get('why', '')))
    if m.get('act') == 'rank':    # raise or lower a story ('' undoes it)
        return bool(re.fullmatch(r'[0-9a-f]{16}', m.get('id', ''))) and m.get('why') in ('up', 'down', '')
    if m.get('act') == 'note':    # a comment to the editors on what he held: its reference, his words, what it showed
        text = str(m.get('why') or '')
        return bool(REF.fullmatch(m.get('id', ''))) and 0 < len(text.strip()) <= NOTE_TEXT and len(m.get('sec') or '') <= NOTE_CTX
    if m.get('act') == 'unnote':  # a comment taken back
        return bool(NOTE_ID.fullmatch(m.get('id', '')))
    if m.get('act') == 'title':   # his own headline for a story or an event page ('' gives it back to the editors)
        t = str(m.get('why') or '')
        return bool(TITLE_ID.fullmatch(m.get('id', ''))) and len(t) <= TITLE_TEXT and '\n' not in t and len(m.get('sec') or '') <= 300
    return m.get('act') == 'undo'


def apply(state, msgs, items, key, now, text):
    """Fold the owner's new actions into state {removed: [...], moved: {id: sec}}; returns how many counted.
    `text(item)` gives the words the radar learns from."""
    done = 0
    for m in msgs:
        if not valid(m, key, now):
            continue
        sid, it = m['id'], items.get(m['id'])
        if m['act'] in ('quote', 'lead'):
            if sid:
                state[m['act']] = {'key' if m['act'] == 'quote' else 'id': sid, 'at': now.isoformat()}
            else:
                state.pop(m['act'], None)
        elif m['act'] == 'pic':
            if m['why']:
                state.setdefault('pics', {})[sid] = {'k': m['why'], 'at': now.isoformat()}
            else:
                state.get('pics', {}).pop(sid, None)
        elif m['act'] == 'rank':
            if m['why']:
                state.setdefault('rank', {})[sid] = {'v': m['why'], 'at': now.isoformat()}
            else:
                state.get('rank', {}).pop(sid, None)
        elif m['act'] == 'note':
            nid = f"n{m['at']}"
            if any(n['id'] == nid for n in state.get('notes') or []):
                continue
            state.setdefault('notes', []).append({'id': nid, 'ref': sid, 'text': ' '.join(str(m['why']).split()),
                                                  'ctx': ' '.join(str(m.get('sec') or '').split()), 'at': now.isoformat()})
        elif m['act'] == 'unnote':
            state['notes'] = [n for n in state.get('notes') or [] if n['id'] != sid]
        elif m['act'] == 'title':
            if str(m['why']).strip():
                state.setdefault('titles', {})[sid] = {'t': ' '.join(str(m['why']).split()), 'was': ' '.join(str(m.get('sec') or '').split()),
                                                       'at': now.isoformat()}
            else:
                state.get('titles', {}).pop(sid, None)
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
    # a raised or lowered story and a chosen main story belong to the news of the moment: two days, one day
    state['rank'] = {k: v for k, v in (state.get('rank') or {}).items() if datetime.fromisoformat(v['at']) >= now - timedelta(days=2)}
    state['pics'] = {k: v for k, v in (state.get('pics') or {}).items() if datetime.fromisoformat(v['at']) >= now - timedelta(days=3)}
    state['notes'] = [n for n in state.get('notes') or [] if datetime.fromisoformat(n['at']) >= now - timedelta(days=NOTE_DAYS)]
    state['titles'] = {k: v for k, v in (state.get('titles') or {}).items() if datetime.fromisoformat(v['at']) >= now - timedelta(
        days=EVENT_TITLE_DAYS if k.startswith('ev:') else TITLE_DAYS)}
    if state.get('lead') and datetime.fromisoformat(state['lead']['at']) < now - timedelta(days=1):
        state.pop('lead')
    return state


def load(path):
    try:
        st = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        st = {}
    out = {'removed': st.get('removed') or [], 'moved': st.get('moved') or {}}
    for k in ('quote', 'lead', 'rank', 'pics', 'notes', 'titles'):
        if st.get(k):
            out[k] = st[k]
    return out
