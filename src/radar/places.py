"""Where an event page's places lie (the owner, 18/10: 'Lad os lave kortet' – DR's overview of France's riots shows its
cities as red dots on France – 'Er tænkeligt at dette kan lade sig gøre automatisk i fremtiden?').

The places the editor names on its event pages (events.json on the digest branch, read by radar.yml into
.cache/events.json) are looked up once each in OpenStreetMap's Nominatim – by its usage policy: at most one request a
second, a User-Agent that names the application, every answer kept – and written to places.json on the data branch:
{'updated', 'places': {"<place>|<kicker>" (lower case): [lat, lon, kind]}}, kind 'country', 'state' or 'city'. The app
draws an event page's map from it. Only place names leave the radar. Stdlib only."""
import json
import time
import urllib.parse
import urllib.request

NOMINATIM = 'https://nominatim.openstreetmap.org/search'
UA = {'User-Agent': 'Khabar/1.0 (+https://khabar.nu; event maps)', 'Accept-Language': 'da,en'}
PER_RUN = 12          # new places looked up in a run (a second apart)
RETRY_DAYS = 3        # a place not found is asked again after this
AREA = {'country', 'state', 'region', 'province', 'county', 'territory', 'archipelago', 'island', 'continent'}


def key(place, kicker):
    return f"{str(place or '').strip().lower()}|{str(kicker or '').strip().lower()}"


def lookup(place, kicker, fetch=None):
    """[lat, lon, kind] for a place (in the kicker's country when the kicker is another name), None when not found."""
    q = place if not kicker or place.strip().lower() == kicker.strip().lower() else f'{place}, {kicker}'
    url = f"{NOMINATIM}?{urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'limit': 1})}"
    if fetch is None:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10) as r:
            got = json.loads(r.read(200_000).decode('utf-8'))
    else:
        got = fetch(url)
    if not got:
        return None
    hit = got[0]
    kind = hit.get('addresstype') or hit.get('type') or ''
    return [round(float(hit['lat']), 4), round(float(hit['lon']), 4), 'country' if kind == 'country' else 'state' if kind in AREA else 'city']


def update(events, memory, now, fetch=None, sleep=time.sleep):
    """places.json as this run leaves it: the places of the event pages looked up, at most PER_RUN new ones."""
    places = dict((memory or {}).get('places') or {})
    missed = dict((memory or {}).get('missed') or {})
    wanted = []
    for e in (events or {}).get('items') or []:
        if not isinstance(e, dict):
            continue
        for p in [*(e.get('places') or []), e.get('kicker')]:
            if p and isinstance(p, str):
                wanted.append((p, e.get('kicker') or ''))
    asked = 0
    for place, kicker in dict.fromkeys(wanted):
        k = key(place, kicker)
        if k in places or (k in missed and (now.timestamp() - missed[k]) < RETRY_DAYS * 86400):
            continue
        if asked >= PER_RUN:
            break
        if asked:
            sleep(1.1)        # Nominatim's policy: one request a second
        asked += 1
        try:
            hit = lookup(place, kicker, fetch)
        except Exception:  # noqa: BLE001 – the service did not answer: next run
            continue
        if hit:
            places[k] = hit
            missed.pop(k, None)
        else:
            missed[k] = now.timestamp()
    keep = {key(p, kk) for p, kk in wanted}
    return {'updated': now.isoformat(timespec='seconds'), 'places': {k: v for k, v in places.items() if k in keep},
            'missed': {k: v for k, v in missed.items() if k in keep}}
