"""How much Khabar is used – for the owner only, readable with the admin code.

The app tells the relay, without the user noticing anything (no question, no button, nothing stored for it):
- each time it is opened (and when it comes back after half an hour away): from the home screen or a browser,
  iPhone, Android or other, the phone's time zone (so the country, never a place) and language, and how it came –
  a notification, a link in WhatsApp, Facebook/Messenger, Google, a text message, another site, or straight;
- once, when someone taps 'Kom i gang' on their very first visit: a new person has started;
- when it goes to the background: how long it was open, which tabs were looked at and how many stories opened.
The stories read and shared come from the signals the app already sends to teach the radar (feedback.py).
No number follows a person, so these are counts, not a record of anyone. The owner's own phone does not count.

Every radar run adds what arrived to state/stats.enc on the data branch: counts per Danish day (and hour), 120
days back – the most read stories 14 days back – and the number of phones with notifications. The file is encrypted
(AES-GCM) with a key made from the admin code, so only the owner's app can read it although the branch is public.
Without ADMIN_KEY (or the cryptography package, which comes with pywebpush) nothing is counted."""
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

KEEP_DAYS = 120
TOP_DAYS = 14         # the most read stories (titles take room)
MAX_PER_RUN = 600     # the relay is public: one run never takes more than this many messages
MAX_KEYS = 40         # nor more than this many time zones, languages or stories a day
OSES = ('ios', 'android', 'other')
VIAS = ('push', 'whatsapp', 'facebook', 'google', 'sms', 'web', 'direct', 'resume')
TABS = ('home', 'dk', 'me', 'world', 'threads', 'latest', 'search')


def dk(t):
    """Danish local time (Europe/Copenhagen; EU summer-time rule where no time zone database is installed)."""
    try:
        from zoneinfo import ZoneInfo
        return t.astimezone(ZoneInfo('Europe/Copenhagen'))
    except Exception:  # noqa: BLE001
        def last_sunday(month):
            d = datetime(t.year, month, 31, 1, tzinfo=timezone.utc)
            return d - timedelta(days=(d.weekday() + 1) % 7)
        summer = last_sunday(3) <= t < last_sunday(10)
        return t.astimezone(timezone(timedelta(hours=2 if summer else 1)))


def key_of(admin):
    """The 32-byte key both the radar and the owner's app make from the admin code (the app does the same in JS)."""
    return hashlib.sha256(b'khabar-stats|' + admin.strip().lower().encode('utf-8')).digest()


def seal(obj, admin):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    ct = AESGCM(key_of(admin)).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), None)
    return base64.b64encode(iv + ct).decode('ascii')   # iv, then the ciphertext with its tag – as WebCrypto reads it


def unseal(text, admin):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(text)
    return json.loads(AESGCM(key_of(admin)).decrypt(raw[:12], raw[12:], None).decode('utf-8'))


def empty_day():
    return {'opens': 0, 'new': 0, 'app': 0, 'ios': 0, 'android': 0, 'other': 0, 'h': [0] * 24,
            'tz': {}, 'lang': {}, 'via': {}, 'secs': 0, 'stays': 0, 'tabs': {}, 'opened': 0, 'top': {}}


def bump(counts, key, n=1):
    if key and (key in counts or len(counts) < MAX_KEYS):
        counts[key] = counts.get(key, 0) + n


def add(stats, msgs, phones, now):
    """Counts what arrived – openings ('visit'), time in the app ('leave'), stories read and shared – into their
    Danish day, forgets old days, and notes the phones with notifications."""
    days = stats.setdefault('days', {})
    for m in msgs[:MAX_PER_RUN]:
        try:
            t = dk(datetime.fromtimestamp(int(m['at']), timezone.utc))
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        d = days.setdefault(t.date().isoformat(), empty_day())
        for k, v in empty_day().items():   # a day counted before a field existed
            d.setdefault(k, v)
        kind = m.get('kind')
        if kind == 'visit':
            d['opens'] += 1
            d['new'] += 1 if m.get('first') else 0
            d['app'] += 1 if m.get('app') else 0
            d[m.get('os') if m.get('os') in OSES else 'other'] += 1
            d['h'][t.hour] += 1
            bump(d['tz'], m.get('tz'))
            bump(d['lang'], m.get('lang'))
            bump(d['via'], m.get('via') if m.get('via') in VIAS else 'direct')
        elif kind == 'leave':
            d['secs'] += max(0, min(4 * 3600, int(m.get('secs') or 0)))
            d['stays'] += 1
            d['opened'] += max(0, min(200, int(m.get('opened') or 0)))
            for tab, n in (m.get('tabs') or {}).items():
                if tab in TABS:
                    bump(d['tabs'], tab, max(0, min(100, int(n))))
        elif kind in ('read', 'share') and m.get('id'):
            top = d['top']
            if m['id'] not in top and len(top) >= MAX_KEYS:   # full: the least read story makes room
                low = min(top, key=lambda k: top[k][1] + top[k][2])
                if top[low][1] + top[low][2] > 1:
                    continue
                del top[low]
            row = top.setdefault(m['id'], [str(m.get('title', ''))[:160], 0, 0])
            row[1 if kind == 'read' else 2] += 1
    today = dk(now).date()
    for day in list(days):
        if day < (today - timedelta(days=KEEP_DAYS)).isoformat():
            del days[day]
        elif day < (today - timedelta(days=TOP_DAYS)).isoformat():
            days[day].pop('top', None)
    stats.setdefault('since', today.isoformat())
    stats['phones'] = phones
    stats['updated'] = now.isoformat()
    return stats


def update(path, admin, msgs, phones, now):
    """One radar run: read the sealed file, add what arrived, seal it again. Never stops the radar."""
    if not admin:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401 – without it: not counted
        stats = {}
        if os.path.exists(path):
            try:
                with open(path, encoding='ascii') as f:
                    stats = unseal(f.read(), admin)
            except Exception:  # noqa: BLE001
                print('stats: the old counts cannot be read (a new admin code?) – counting afresh')
        stats = add(stats, msgs, phones, now)
        with open(path, 'w', encoding='ascii') as f:
            f.write(seal(stats, admin))
        return stats
    except Exception as e:  # noqa: BLE001 – statistics are a bonus (a missing package …)
        print('stats: not counted this run:', e)
        return None
