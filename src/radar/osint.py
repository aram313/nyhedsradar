"""The map for Khabar's Kort tab: the latest attacks and armed events in the news, placed where they happened.

Runs after every radar pass (radar.yml, after the energy step) and writes `map.json` into the state folder, which is saved
on the data branch the app reads. Stdlib only, no network: it reads this pass's data.json (the stories, with the
editor's headline from summaries.json where he wrote one, RADAR_SUMMARIES).

A story is an event when its headline says something violent happened – a strike, a drone, a missile, shelling, an
explosion, clashes, people killed – and not only that someone threatens, warns or plans it. It is placed at the most
specific place its headline names (config/map-places.json: a city, camp or site before a region or sea, before a
country; among equals the one after 'in/on/near/i/ved/mod'); a capital that only speaks ('Moscow says …') is no place.
A story placed only by its country is marked approximate. The kind (luft, drone, missil, artilleri, eksplosion, sø,
kamp, angreb) is the first that its words show, in that order.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / 'config'
HOURS = 72          # how far back the map looks
LIMIT = 300         # at most this many events

# the kinds, most telling first; English and Danish (the radar has every headline in one of the two)
KINDS = [
    ('luft', r'air ?strikes?|airstrikes?|air raids?|warplanes?|fighter jets?|bombing|bombed|bombs?|bombard\w*|'
             r'luftangreb\w*|kampfly\w*|bombe\w*|bombard\w*'),
    ('drone', r'drones?|uavs?|droner?\w*|droneangreb\w*'),
    ('missil', r'missiles?|rockets?|ballistic|projectiles?|missil\w*|raket\w*|ballistisk\w*'),
    ('artilleri', r'shelling|shelled|artillery|mortars?|beskydning\w*|beskød|artilleri\w*|granat\w*'),
    ('eksplosion', r'explosions?|blast|exploded|landmines?|(?:a|sea|naval) mines?|ieds?|car bomb|'
                   r'suicide bomb\w*|eksplosion\w*|eksploderede|landmine\w*|sømine\w*|en mine|bilbombe\w*|'
                   r'selvmordsbombe\w*'),
    ('sø', r'(?:tanker|ship|vessel|freighter|tankskib\w*|skib\w*|fartøj\w*)'),
    ('kamp', r'clash(?:es|ed)?|gunfire|gunmen|ambush\w*|raids?|raided|stormed|incursions?|firefight|fighting|'
             r'sammenstød|skudveksling\w*|razzia\w*|stormede|kampe(?:ne)?|skud'),
    ('angreb', r'attacks?|attacked|strikes?|struck|hit|hits|killed|kills|dead|wounded|injured|massacre|'
               r'angreb\w*|angriber|angrebet|ramt|rammer|dræbt\w*|dræber|døde|sårede?|massakre\w*'),
]
KIND_RE = [(k, re.compile(rf'(?<![\w-])(?:{p})(?![\w-])', re.I)) for k, p in KINDS]
# a ship is an event only when something happens to it
SEA_HIT = re.compile(r'(?<![\w-])(?:attack\w*|hit|struck|seized|fire|ablaze|explo\w*|mines?|angreb\w*|ramt|brand|'
                     r'kapre\w*|beslaglagt|eksplo\w*|en mine)(?![\w-])', re.I)
# words that say it happened: with one of them, a headline is an event even beside a warning or a plan
HAPPENED = re.compile(r'(?<![\w-])(?:killed|kills|dead|wounded|injured|struck|exploded|dræbt\w*|dræber|døde|'
                      r'sårede?|ramt|ramte|eksploderede)(?![\w-])', re.I)
# words that make violence a threat, a plan or a metaphor, not an event
NOT_EVENT = re.compile(
    r'(?<![\w-])(?:threat\w*|warns?|warned|vows?|plans?|planned|could|would|if|ready to|prepares? to|maybe|perhaps|'
    r'exercises?|drills?|patrol\w*|truer|advarer|lover|planlægger|planlagt|hvis|klar til|måske|øvelse\w*|'
    r'flyvning\w*|patrulje\w*)(?![\w-])', re.I)
# never an armed event, whatever else the headline says
NEVER = re.compile(r'(?<![\w-])(?:cyber\w*|hunger strike|general strike|strike action|strikes? (?:a )?deal|'
                   r'cyberangreb\w*|sultestrejke|generalstrejke|strejke\w*|anniversary|årsdag|memorial|mindes|'
                   r'match|football|fodbold|film|movie|series|serie|earthquakes?|jordskælv\w*|floods?|'
                   r'oversvømmelse\w*|wildfires?|skovbrand\w*|stormvejr|hurricanes?|orkan\w*|'
                   r'workers?|unions?|walkouts?|on strike|arbejdere|fagforening\w*|rules out|udelukker|starvation|famine|hunger|sult|hungersnød|analysis|analyse)(?![\w-])', re.I)
# a reaction to an attack (a condemnation, a denial, a defence) is not the attack: it counts only when the headline
# also names the town and says what happened there
REACT = re.compile(r'(?<![\w-])(?:condemns?|condemned|denies|denied|defends?|slams?|criticis\w*|criticiz\w*|calls|'
                   r'blames?|accus\w*|fordømmer|fordømte|benægter|afviser|forsvarer|kritiserer|kalder|anklage\w*|'
                   r'giver \w+ skylden|skylden|reagerer|i tvivl|report|rapport)(?![\w-])', re.I)
# an outlet's name in front of its headline ('Jerusalem Daily: …') names no place
OUTLET_HEAD = re.compile(r'^[^:]{0,40}\b(?:daily|news|post|times|network|tv|radio|agency|press|media|today|'
                         r'analyse|analysis)\b[^:]*:\s*', re.I)
NOT_PLACE = {'hamas'}       # 'Hama' + a genitive s
# a capital at the head of the headline that only speaks is the government, not a place
SPEAKS = re.compile(r'^\s*(?:\S+\s+){0,1}?(?:says?|said|warns?|claims?|accuses?|denies|announces?|tells|urges|'
                    r'siger|sagde|advarer|anklager|afviser|meddeler|kalder|opfordrer)\b', re.I)
NEAR = re.compile(r'(?:\b(?:in|on|near|at|outside|into|across|over|off|against|i|ved|nær|mod|på|over|uden for|syd for|'
                  r'nord for|øst for|vest for)\s+(?:the\s+|det\s+|den\s+)?(?:\w+\s+){0,2})$', re.I)
RANK = {'s': 3, 'r': 2, 'c': 1}


def now():
    return datetime.now(timezone.utc)


def load_places(path=None):
    """The gazetteer as one regular expression of every name (longest first) and name -> place."""
    data = json.loads(Path(path or CONFIG / 'map-places.json').read_text(encoding='utf-8'))
    by_name = {}
    for name_da, kind, lat, lon, names in data['places']:
        for n in names:
            by_name.setdefault(n.lower(), {'pl': name_da, 'kind': kind, 'la': lat, 'lo': lon})
    pat = '|'.join(re.escape(n) for n in sorted(by_name, key=len, reverse=True))
    # a Danish genitive ('Adens lufthavn') and a compound ('Riyadh-lufthavnen', 'Jabalia-lejren') name the place too
    return re.compile(rf"(?<!\w)(?P<n>{pat})s?(?!\w)", re.I), by_name


def place_of(text, places):
    """The place a headline's event happened: the most specific one named, the one after a preposition among equals;
    a capital that only speaks ('Moscow says …') does not count. None when no place is named."""
    rx, by_name = places
    text = OUTLET_HEAD.sub('', text or '')
    found = []
    for m in rx.finditer(text):
        if m.group(0).lower() in NOT_PLACE:
            continue
        p = by_name[m.group('n').lower()]
        if p['kind'] == 's' and SPEAKS.match(text[m.end():]) and not text[:m.start()].strip():
            continue
        found.append((p, bool(NEAR.search(text[:m.start()])), m.start()))
    if not found:
        return None
    top = max(RANK[p['kind']] for p, _, _ in found)
    best = [f for f in found if RANK[f[0]['kind']] == top]
    near = [f for f in best if f[1]]
    if near:
        return near[0][0]
    # countries only: the one named last is the one acted on ('Israel strikes Lebanon'); else the first
    return (best[-1] if top == 1 else best[0])[0]


def kind_of(text):
    """The event's kind, or None when the headline tells of no violent event."""
    t = text or ''
    if NEVER.search(t) or (NOT_EVENT.search(t) and not HAPPENED.search(t)):
        return None
    for k, rx in KIND_RE:
        if rx.search(t):
            if k == 'sø' and not SEA_HIT.search(t):
                continue
            return k
    return None


def editor_titles(summaries):
    """The editor's checked headlines: article id -> headline (as run.editor_titles; this step imports nothing)."""
    out, at = {}, {}
    for k, v in ((summaries or {}).get('titles') or {}).items():
        if not isinstance(v, dict) or not v.get('title'):
            continue
        for i in [k, *(v.get('members') or [])]:
            if i not in out or str(v.get('at') or '') > at[i]:
                out[i], at[i] = v['title'], str(v.get('at') or '')
    return out


def events(items, places, titles=None, hours=HOURS, limit=LIMIT, t=None):
    titles = titles or {}
    cut = (t or now()) - timedelta(hours=hours)
    out, seen = [], set()
    for it in items:
        if it.get('id') in seen or it.get('kind') == 'kommentar':
            continue
        when = it.get('published') or it.get('found')
        try:
            if not when or datetime.fromisoformat(when) < cut:
                continue
        except ValueError:
            continue
        # a story Live shows or a big one; a single unverified channel's post is not enough for the map
        if not (it.get('live') or it.get('big') or (it.get('outlets') or 1) >= 2):
            continue
        ed = next((titles[k] for k in [it.get('id'), *(it.get('members') or [])] if k in titles), None)
        texts = [x for x in (ed, it.get('title_da'), it.get('title_tr'), it.get('title') if it.get('lang') != 'ar' else None) if x]
        text = ' · '.join(texts)
        kind = kind_of(text)
        if not kind:
            continue
        place = next((p for p in (place_of(x, places) for x in texts) if p), None)
        if not place:
            continue
        rough = place['kind'] == 'c'
        # a reaction needs a town and what happened there; a country alone needs what happened or a telling kind
        if REACT.search(text) and (rough or not HAPPENED.search(text)):
            continue
        if rough and kind == 'angreb' and not HAPPENED.search(text):
            continue
        seen.add(it.get('id'))
        out.append({'i': it.get('id'), 'k': kind, 'pl': place['pl'], 'la': place['la'], 'lo': place['lo'],
                    'ca': place['kind'] == 'c', 't': ed or it.get('title_da') or it.get('title_tr') or it.get('title'),
                    'ed': bool(ed), 's': it.get('source'), 'p': when, 'u': it.get('link'), 'n': it.get('outlets') or 1,
                    'big': bool(it.get('big')), 'sec': it.get('sec')})
    out.sort(key=lambda e: e['p'], reverse=True)
    return out[:limit]


def run(state, summaries=None):
    def load(p):
        try:
            return json.loads(Path(p).read_text(encoding='utf-8'))
        except Exception:
            return {}
    items = load(Path(state) / 'data.json').get('items', [])
    titles = editor_titles(load(summaries or os.environ.get('RADAR_SUMMARIES') or '__none__'))
    out = {'updated': now().isoformat(), 'events': events(items, load_places(), titles)}
    (Path(state) / 'map.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out


def main():
    state = Path(os.environ.get('RADAR_STATE', Path(__file__).resolve().parents[2] / 'state'))
    out = run(state)
    ev = out['events']
    print(f"map: {len(ev)} events, {sum(1 for e in ev if not e['ca'])} placed exactly, kinds "
          f"{sorted({e['k'] for e in ev})}")


if __name__ == '__main__':
    main()
