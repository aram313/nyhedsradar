"""Send Web Push notifications to the phones that signed up in the app.

A phone signs up by itself: the app posts its push address to the private relay topic, the radar picks it up on
its next run (feedback.pull) and keeps it in state/phones.bin, encrypted with PROFILE_KEY because the data branch
is public. Addresses from the older PUSH_SUBS secret are still used too. An address the push service reports as
gone (404/410) is dropped."""
import base64
import hashlib
import json
import os
import tempfile
from urllib.parse import urlparse

# the push services of Chrome/Android, Firefox, Safari/iPhone and Edge; any other address is no phone of ours
HOSTS = ('fcm.googleapis.com', 'push.services.mozilla.com', 'push.apple.com', 'notify.windows.com')
MAX_PHONES = 300
NEW_PER_DAY = 30
# the kinds of notification a phone can ask for (the app's switches, pro-plan 5.5): top stories, the day's recap at 21
# and Hizb ut-Tahrir's new answers. A phone that signed up before the switches gets what it had: top and digest.
KINDS = ('top', 'digest', 'svar')
BEFORE = ['top', 'digest']


def valid(sub):
    """A subscription as the browser makes it: an https endpoint at a known push service and its two keys."""
    if not isinstance(sub, dict):
        return False
    url, keys = sub.get('endpoint'), sub.get('keys') or {}
    if not isinstance(url, str) or len(url) > 1000 or not isinstance(keys, dict):
        return False
    u = urlparse(url)
    host = (u.hostname or '').lower()
    return (u.scheme == 'https' and any(host == h or host.endswith('.' + h) for h in HOSTS)
            and all(isinstance(keys.get(k), str) and 0 < len(keys[k]) < 200 for k in ('p256dh', 'auth')))


def _fernet(secret):
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'khabar-phones|' + secret.encode()).digest()))


def load_phones(path, secret):
    """The phones that signed up by themselves; nothing (and no error) without the key or the file."""
    if not secret or not os.path.exists(path):
        return []
    try:
        with open(path, 'rb') as f:
            return json.loads(_fernet(secret).decrypt(f.read()).decode('utf-8'))
    except Exception as e:  # noqa: BLE001 – a broken file must not stop the radar
        print('phones: could not read the list:', e)
        return []


def save_phones(path, secret, phones):
    if not secret:
        return
    with open(path, 'wb') as f:
        f.write(_fernet(secret).encrypt(json.dumps(phones, separators=(',', ':')).encode('utf-8')))


def wants(signal):
    """The kinds a sign-up asks for, or None when it says nothing (an app from before the switches)."""
    w = signal.get('want')
    return [k for k in KINDS if k in w] if isinstance(w, list) else None


def sign_up(phones, signals, now, today):
    """Adds new phones and removes the ones that switched off; at most NEW_PER_DAY new a day and MAX_PHONES in all,
    so nobody can flood the list through the public relay. `today` = phones added in the last 24 hours. A phone that
    signs up again with other switches keeps its place and gets its new choice (nothing else about it is kept)."""
    have = {p['endpoint'] for p in phones}
    for s in signals:
        sub = s.get('sub')
        if not valid(sub):
            continue
        want = wants(s)
        if s['kind'] == 'unsub':
            phones = [p for p in phones if p['endpoint'] != sub['endpoint']]
            have.discard(sub['endpoint'])
        elif sub['endpoint'] in have:
            if want is not None:
                phones = [{**p, 'want': want} if p['endpoint'] == sub['endpoint'] else p for p in phones]
        elif today < NEW_PER_DAY and len(phones) < MAX_PHONES:
            phones.append({'endpoint': sub['endpoint'], 'keys': {k: sub['keys'][k] for k in ('p256dh', 'auth')}, 'at': now,
                           **({'want': want} if want is not None else {})})
            have.add(sub['endpoint'])
            today += 1
    return phones


def everyone(phones, kind=None):
    """The signed-up phones plus the ones from the PUSH_SUBS secret (the owner's: every kind), each once; with a kind,
    only the phones that asked for it."""
    out, seen = [], set()
    for sub in json.loads(os.environ.get('PUSH_SUBS') or '[]') + phones:
        if isinstance(sub, dict) and sub.get('endpoint') and sub['endpoint'] not in seen:
            if kind and kind not in (sub.get('want') if isinstance(sub.get('want'), list) else (BEFORE if 'at' in sub else KINDS)):
                continue
            seen.add(sub['endpoint'])
            out.append({'endpoint': sub['endpoint'], 'keys': sub.get('keys', {})})
    return out


def send(payload, subs=None):
    subs = everyone([]) if subs is None else subs
    key = os.environ.get('VAPID_PRIVATE', '').strip()
    if not subs or not key:
        return {'sent': 0, 'skipped': 'no subscribers or no key'}
    from pywebpush import WebPushException, webpush

    with tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False) as f:
        f.write(key)
        key_path = f.name
    sent, failed, gone = 0, [], []
    try:
        for sub in subs:
            try:
                webpush(subscription_info=sub, data=json.dumps(payload, ensure_ascii=False),
                        vapid_private_key=key_path,
                        vapid_claims={'sub': os.environ.get('VAPID_SUBJECT', 'mailto:nyhedsradar@example.invalid')},
                        ttl=3 * 3600)
                sent += 1
            except WebPushException as e:
                code = getattr(e.response, 'status_code', None)
                if code in (404, 410):
                    gone.append(sub['endpoint'])
                failed.append('expired' if code in (404, 410) else str(code or e)[:80])
    finally:
        os.unlink(key_path)
    return {'sent': sent, 'failed': failed, 'gone': gone}
