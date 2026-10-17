"""One radar run: fetch every source, score new items against the group's taste,
find stories many outlets cover at once, write data.json for the app, send notifications."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from radar import admin, analyses, feedback, level, push, stats
from radar.translate import VERSION as TR_VERSION, Translator, tidy
from radar.feeds import fetch_all, tidy as tidy_headline
from radar.headlines import clean_teaser, commentary, curious
from radar.method import Method
from radar.sections import Sections

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'config'
STATE = Path(os.environ.get('RADAR_STATE', ROOT / 'state'))
CACHE = Path(os.environ.get('RADAR_CACHE', ROOT / '.cache'))
NOW = datetime.now(timezone.utc)
READABLE = {'da', 'en'}   # languages the owner reads; others are translated or used only as signal
# the kinds of media an opened story takes turns between (feeds.json 'group'), in this order
KINDS = ('dk', 'west', 'mena', 'il', 'east', 'official', 'channel', 'bevægelsen')


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def ts(iso):
    return datetime.fromisoformat(iso)


# ------------------------------------------------------------------ embeddings

class Embedder:
    def __init__(self, model):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name=model, cache_dir=str(CACHE / 'fastembed'))

    def __call__(self, texts):
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        e = np.array(list(self.model.embed(texts, batch_size=64)), dtype=np.float32)
        return e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-9)


def load_profile(embed):
    """The group's shared links, embedded once and cached by content hash."""
    path = CACHE / 'profile.jsonl'
    raw = path.read_bytes()
    key = hashlib.sha1(raw).hexdigest()[:12]
    cached = CACHE / f'profile-{key}.npz'
    rows = [json.loads(l) for l in raw.decode('utf-8').splitlines() if l.strip()]
    if cached.exists():
        m = np.load(cached)['m'].astype(np.float32)
    else:
        m = embed([r['t'] for r in rows])
        np.savez_compressed(cached, m=m.astype(np.float16))
    # newer shares count more: weight 1.0 today, ~0.68 after one year, never below 0.5
    age = np.array([(NOW.date() - datetime.fromisoformat(r['d']).date()).days for r in rows], dtype=np.float32)
    w = 0.5 + 0.5 * np.exp(-age / 365)
    return m, w


def relevance(e, m, w, k, item_ids=None, prof_ids=None):
    """Weighted mean similarity to the k closest profile entries. An item never counts as
    evidence for itself (community items are both scored and part of the profile)."""
    sims = e @ m.T
    if item_ids is not None and prof_ids is not None:
        pos = {pid: j for j, pid in enumerate(prof_ids) if pid}
        for i, iid in enumerate(item_ids):
            if iid in pos:
                sims[i, pos[iid]] = -1
    k = min(k, sims.shape[1])
    idx = np.argpartition(-sims, k - 1, axis=1)[:, :k]
    top = np.take_along_axis(sims, idx, axis=1)
    wt = w[idx]
    return (top * wt).sum(axis=1) / wt.sum(axis=1)


# ------------------------------------------------------------------ helpers

# liveblogs, podcasts, videos, sport, celebrity and lifestyle never belong in the radar
NOISE_TITLE = re.compile(r'^(live\b|live:|liveblog|watch\b|video\b|podcast\b|quiz\b|horoskop|se billederne)'
                         r'|seneste nyt|\blive blog\b|\bliveblog\b|\blive updates\b|\blive:'
                         r'|følg (med|udviklingen)|se med her'
                         # an outlet's hub page, not a story: 'Latin American News | Latest Latin American News'
                         r'|^[^|:]{1,40}\bnews\s*\||\blatest [^|:]{0,40}\bnews\s*$|\bnews (?:and|&) headlines\b|^top stories\b', re.I)
NOISE_URL = re.compile(r'/(sport|sports|fodbold|football|soccer|haandbold|cykling|tennis|golf|formel-1|kendte|celebrity|'
                       r'underholdning|entertainment|livsstil|lifestyle|horoskop|vejret|weather|quiz|games|podcasts?|'
                       r'travel|rejser|mad|food|recipes|opskrifter|bolig|motor|biler|tv-guide|musik|music|film-og-serier)(/|-|$)', re.I)


# a headline that is one attributed statement: "Kremlin: ...", "Trump: ...", "Det jordanske udenrigsministerium: ..."
STATEMENT = re.compile(r'^(?!(?:analyse|analysis|kommentar|leder|opinion|debat|interview|explainer|guide|quiz|live|video|'
                       r'watch|podcast|breaking|update|opdatering)\b)[^:\n]{2,60}:\s+\S.{10,}', re.I)

# an English headline built around what someone said: "Zelenskiy says ...", "Iran warns ..."
SAYS = re.compile(r'^\S.{0,60}?\b(says|said|warns|tells|vows|urges|calls on|claims|denies|confirms|announces|rejects)\b', re.I)


# 'strike' in war news is an attack, but the English-Danish model makes it a labour strike ('strejke')
WAR_STRIKE = re.compile(r'\b((?:air|drone|missile|israeli|russian|ukrainian|us|u\.s\.|military|deadly|fresh|new|overnight|'
                        r'retaliatory|precision|houthi)\s+)strikes?\b|\bstrikes(?=\s+(?:on|against|targeting|hit))',
                        re.I)


def military(text):
    def swap(m):
        word = 'attacks' if m.group(0).lower().endswith('s') else 'attack'
        return (m.group(1) or '') + (word.capitalize() if not m.group(1) and m.group(0)[0].isupper() else word)
    return WAR_STRIKE.sub(swap, text)


def is_noise(item):
    return bool(item.get('removed') or NOISE_TITLE.search(item['title'].strip()) or NOISE_URL.search(item['link']))



def norm_title(t):
    return re.sub(r'\W+', ' ', t.lower()).strip()[:90]


def percentile(scores_sorted, s):
    if len(scores_sorted) == 0:
        return 50
    return int(100 * np.searchsorted(scores_sorted, s, side='left') / len(scores_sorted))


def top_share(scores_sorted, s):
    """Where a story stands in its section, 0 (last) to 100 (first); ties share the better place, so the
    best story of a small section still reaches the top."""
    n = len(scores_sorted)
    if n <= 1:
        return 100
    return int(100 * (np.searchsorted(scores_sorted, s, side='right') - 1) / (n - 1))


def place_finder(cfg):
    """The cities a headline names (config/places.json): Latin spellings as whole words (a Danish genitive -s
    allowed), Arabic ones anywhere in the word, since Arabic glues 'in' and 'to' onto the name."""
    pats = []
    for city, names in cfg.items():
        if city.startswith('_'):
            continue
        latin = [re.escape(n) for n in names if not re.search('[؀-ۿ]', n)]
        arabic = [re.escape(n) for n in names if re.search('[؀-ۿ]', n)]
        parts = ([r'\b(?:' + '|'.join(latin) + r")(?:'?s)?\b"] if latin else []) + (['|'.join(arabic)] if arabic else [])
        pats.append((city, re.compile('|'.join(parts))))
    return lambda text: frozenset(city for city, pat in pats if pat.search(text or ''))


def clusters(emb, order, threshold, langs=None, strict=None, places=None, other_city=1.01):
    """Group items about the same story. Each item joins the existing story whose centre it is
    closest to (if close enough), otherwise starts a new one. Comparing with the centre rather
    than with any single member keeps a day of different Gaza stories from melting into one."""
    centres, sums, groups, glang, gcity = [], [], [], [], []
    strict = strict or {}
    for i in order:
        e = emb[i]
        lang = langs[i] if langs else ''
        city = places[i] if places else frozenset()
        joined = False
        if centres:
            sims = np.array(centres) @ e
            for j in np.argsort(-sims)[:5]:
                # the model rates any two texts in some languages (Arabic) as rather alike – some unrelated Arabic
                # headlines land almost on top of each other – so a story made only of such texts needs a closer
                # match (settings: same_story_strict; above 1 means such texts never join each other)
                need = strict.get(lang, threshold) if glang[j] == {lang} else threshold
                # the same kind of event in another city (a protest in Copenhagen, one in London) is another story
                # unless the texts are all but the same (settings: same_story_other_city)
                if city and gcity[j] and not city & gcity[j]:
                    need = max(need, other_city)
                if sims[j] >= need:
                    glang[j].add(lang)
                    gcity[j] = gcity[j] | city
                    groups[j].append(i)
                    sums[j] = sums[j] + e
                    centres[j] = sums[j] / np.linalg.norm(sums[j])
                    joined = True
                    break
                if sims[j] < threshold:
                    break
        if not joined:
            centres.append(e.copy()); sums.append(e.copy()); groups.append([i]); glang.append({lang}); gcity.append(city)
    return groups


def load_learned_embeddings(embed, learned, path=None):
    """Embeddings of self-learned entries, cached between runs so each is computed once."""
    path = path or STATE / 'learned_emb.npz'
    cache = {}
    if path.exists():
        z = np.load(path, allow_pickle=False)
        cache = dict(zip(z['ids'].tolist(), z['m'].astype(np.float32)))
    keys = [f"{l['why']}:{l['id']}" for l in learned]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    for i, e in zip(missing, embed([learned[i]['t'] for i in missing])):
        cache[keys[i]] = e
    if not keys:
        return np.zeros((0, 384), dtype=np.float32)
    out = np.array([cache[k] for k in keys], dtype=np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, ids=np.array(keys, dtype='U48'), m=out.astype(np.float16))
    return out


def local_now(settings):
    """Now in Danish time (wall clock; the date and hour are what matter)."""
    try:
        return NOW.astimezone(ZoneInfo(settings['timezone']))
    except Exception:  # no time zone database (plain Windows): Danish summer/winter time by EU rule
        def last_sunday(month):
            d = datetime(NOW.year, month, 31, 1, tzinfo=timezone.utc)
            return d - timedelta(days=(d.weekday() + 1) % 7)
        return NOW + timedelta(hours=2 if last_sunday(3) <= NOW < last_sunday(10) else 1)


def in_quiet_hours(settings):
    start, end = settings['quiet_hours']
    h = local_now(settings).hour
    return h >= start or h < end if start > end else start <= h < end


def editor_titles(summaries):
    """The editor's checked headlines (summaries.json 'titles' on the digest branch): article id -> headline, filed
    under the story's id and its members, the newest winning – as the app reads them (readSummaries in app.js)."""
    out, at = {}, {}
    for k, v in ((summaries or {}).get('titles') or {}).items():
        if not isinstance(v, dict) or not v.get('title'):
            continue
        for i in [k, *(v.get('members') or [])]:
            if i not in out or str(v.get('at') or '') > at[i]:
                out[i], at[i] = v['title'], str(v.get('at') or '')
    return out


def push_headline(it, titles):
    """A notification says the news as the app shows it (the owner's headline rule of 2026-10-17): the editor's
    headline for the story or one of its articles, else the Danish, the English translation, the outlet's own; a
    curiosity headline gives way to its teaser's first sentence."""
    ids = [it['id'], *(it.get('members') or []), *(a.get('id') for a in it.get('also') or [])]
    ed = next((titles[i] for i in ids if titles.get(i) and not curious(titles[i])), '')
    if ed:
        return ed
    head = it.get('title_da') or it.get('title_tr') or it['title']
    if curious(head):
        teaser = clean_teaser(it.get('summary_da') or it.get('summary_tr') or it.get('summary') or '', head)
        first = re.split(r'(?<=[.!?])\s+', teaser, maxsplit=1)[0].rstrip('.') if teaser else ''
        if len(first) >= 25 and not curious(first):
            return first if len(first) <= 140 else first[:138].rsplit(' ', 1)[0] + ' …'
    return head


# ------------------------------------------------------------------ main

def main():
    s = load(CONFIG / 'settings.json', {})
    feeds = [f for f in load(CONFIG / 'feeds.json', []) if not f.get('disabled')]  # the caretaker can switch a dead source off
    outlet_of = {f['name']: f.get('outlet', f['name']) for f in feeds}
    max_age = {f['name']: f.get('max_age_hours', s['max_age_hours']) for f in feeds}
    community = {f['name'] for f in feeds if f.get('community')}
    # Telegram and YouTube channels are fast but unverified (unless a news outlet runs them: `official`);
    # everything else is an established outlet
    channel = {f['name'] for f in feeds if f.get('type') in ('telegram', 'youtube') and not f.get('official')}
    # wire sources post one-line statements ("Kremlin: ..."); they count as an outlet on a story and feed the
    # 'Bevægelser' briefing, but never become a card of their own
    wire = {f['name'] for f in feeds if f.get('wire')}
    label_of = {f['name']: f.get('label', f['name']) for f in feeds}   # readable names (Arabic ones in Latin script)
    # which kind of media each source is (Danish, Western, Arab/Muslim, Israeli, channel), shown with every story
    group_of = {f['name']: f.get('group') or ('channel' if f['name'] in channel else 'dk' if f.get('lang') == 'da' else 'west')
                for f in feeds}
    hint = {f['name']: f['sec'] for f in feeds if f.get('sec')}   # where a source's stories usually belong
    # the state or bloc whose view a source carries ('camp'); the coverage of a story is compared by camp
    camp_of = {f['name']: f.get('camp') or ('channel' if f['name'] in channel else 'dk' if f.get('lang') == 'da' else '')
               for f in feeds}
    # the movement's own outlets never count as an outlet or as confirmation of a fact, and never lead a story
    # another outlet carries; governments' own channels (group 'official') never lead one either
    movement = {f['name'] for f in feeds if 'bevægelsen' in (f.get('camp'), f.get('group'))}
    official = {f['name'] for f in feeds if f.get('group') == 'official'}
    # sources added for their camp's view (scale: false) are ranked against the established sources' scale and
    # never move it: not the taste percentiles, not a section's bar, not the outlet count of the rank or a big story
    off_scale = {f['name'] for f in feeds if f.get('scale') is False}
    # how well a source serves the editor (measured 2026-10-17, docs/hjerne/kilder-maaling.md): a small weight in the
    # rank, and above all which outlet leads a story
    fit_of = {f['name']: float(f.get('fit') or 1.0) for f in feeds}
    feed_of = {f['name']: f for f in feeds}
    sections = Sections(load(CONFIG / 'sections.json', {}))
    find_cities = place_finder(load(CONFIG / 'places.json', {}))
    city_of = lambda it: find_cities(f"{it['title']} {it.get('title_tr') or ''}")

    items = load(STATE / 'items.json', {})          # id -> every scored item from the last keep_hours
    seen = load(STATE / 'seen.json', {})            # id -> first seen; stops dropped items coming back
    learned = load(STATE / 'learned.json', [])      # what the radar taught itself: {id, t, at, why}
    pushes = load(STATE / 'pushes.json', {'sent': [], 'pending': [], 'notified': []})
    relay = load(STATE / 'relay.json', {'since': None})
    health = load(STATE / 'health.json', {})        # source -> runs in a row it failed
    digest = load(os.environ.get('RADAR_DIGEST', CACHE / 'digest.json'), {})  # written by the Claude editor
    live_plan = load(os.environ.get('RADAR_LIVE', CACHE / 'live.json'), {})    # the editor's level for Live (level.py)
    # the editor's headlines (summaries.json on the digest branch): a notification says what the app shows
    ed_titles = editor_titles(load(os.environ.get('RADAR_SUMMARIES', CACHE / 'summaries.json'), {}))
    admitted = load(STATE / 'admitted.json', {})    # member id -> when its story was first admitted to Live
    phones = push.load_phones(STATE / 'phones.bin', os.environ.get('PROFILE_KEY', ''))   # signed up in the app
    owner = admin.load(STATE / 'removed.json')      # what the owner removed or moved with a long press in the app
    emb_store = {}
    if (STATE / 'emb.npz').exists():
        z = np.load(STATE / 'emb.npz', allow_pickle=False)
        emb_store = dict(zip(z['ids'].tolist(), z['m'].astype(np.float32)))
    first_run = len(items) < 300

    fetched, status = fetch_all(feeds)
    health = {name: 0 if st['ok'] else health.get(name, 0) + 1 for name, st in status.items()}
    # the headline rules (feeds.tidy) also hold for what earlier runs kept: a site's name cut off, a blog or a betting
    # ad left out, a channel's 'Who:' line joined to what was said – done once, changes nothing a second time
    for k in list(items):
        f = feed_of.get(items[k]['source'])
        if f and (f.get('drop') or f.get('cut') or f.get('type') in ('gnews', 'telegram')):
            if not tidy_headline(items[k], f) or len(norm_title(items[k]['title']).split()) < 4:
                del items[k]
        elif f and items[k].get('summary'):   # the teaser's call to action, link or picture caption (2026-10-17)
            tidy_headline(items[k], f)

    # 1. keep fresh, unseen, de-duplicated items (same link, or same headline from two feeds)
    known_titles = {norm_title(i['title']) for i in items.values()}
    new = []
    for it in fetched:
        pub = ts(it['published']) if it['published'] else NOW
        if NOW < pub <= NOW + timedelta(hours=12):   # a feed that stamps local time as GMT (Jerusalem Post: +3 h)
            pub = NOW
        if pub > NOW or NOW - pub > timedelta(hours=max_age.get(it['source'], 48)):
            continue
        nt = norm_title(it['title'])
        if len(nt.split()) < 4 or is_noise(it):  # section pages, teasers, liveblogs, sport, celebrity …
            continue
        if it['id'] in seen or it['id'] in items or nt in known_titles:
            continue
        known_titles.add(nt)
        seen[it['id']] = NOW.isoformat()
        it.update(published=pub.isoformat(), found=NOW.isoformat(), community=it['source'] in community)
        new.append(it)

    embed = Embedder(s['model'])

    def text(i):
        return f"{i['title']}. {i.get('summary', '')[:220]}"

    for it, e in zip(new, embed([text(i) for i in new])):
        items[it['id']] = it
        emb_store[it['id']] = e

    # 2. forget what is too old
    keep_from = NOW - timedelta(hours=s['keep_hours'])
    items = {k: v for k, v in items.items() if ts(v['found']) >= keep_from}
    emb_store = {k: v for k, v in emb_store.items() if k in items}
    seen = {k: v for k, v in seen.items() if ts(v) >= NOW - timedelta(days=7)}

    # 3. self-learning: community sources, big stories and copy taps feed the profile automatically
    learned = [l for l in learned if ts(l['at']) >= NOW - timedelta(days=s['learn_days'])]
    learned_ids = {l['id'] for l in learned}
    # one community source teaches at most a few stories a day, so a busy channel cannot take over the taste
    taught = {}
    for l in learned:
        if l['why'] == 'community' and l['id'] in items and ts(l['at']) >= NOW - timedelta(hours=24):
            taught[items[l['id']]['source']] = taught.get(items[l['id']]['source'], 0) + 1
    for it in new:
        if it['community'] and it['id'] not in learned_ids and taught.get(it['source'], 0) < s.get('learn_per_source_day', 10):
            learned.append({'id': it['id'], 't': text(it), 'at': it['found'], 'why': 'community'})
            learned_ids.add(it['id'])
            taught[it['source']] = taught.get(it['source'], 0) + 1
    taps, relay['since'] = feedback.pull(relay['since'])
    # phones sign up by themselves through the same relay (push.py keeps them, encrypted)
    signups = [x for x in taps if x['kind'] in ('sub', 'unsub')]
    # the owner's own actions, signed with the admin code (admin.py ignores anything unsigned)
    acted = admin.apply(owner, [x for x in taps if x['kind'] == 'admin'], items, os.environ.get('ADMIN_KEY', ''), NOW, text)
    visits = [x for x in taps if x['kind'] in ('visit', 'leave')]   # the app opened and left: statistics (stats.py)
    taps = [x for x in taps if x['kind'] not in ('sub', 'unsub', 'admin', 'visit', 'leave')]
    added = sum(1 for p in phones if p.get('at') and ts(p['at']) >= NOW - timedelta(hours=24))
    phones = push.sign_up(phones, signups, NOW.isoformat(), added)
    # the relay topic is readable in the public app, so anyone could post to it: learn only from stories the
    # radar itself has, with the radar's own text, and at most a few dozen signals a day
    today = sum(1 for l in learned if l['why'] in ('copied', 'read') and ts(l['at']) >= NOW - timedelta(hours=24))
    for tap in taps:   # shared or copied = strong "more like this"; opened to read = a milder one
        it = items.get(tap.get('id'))
        if not it or today >= s.get('max_signals_per_day', 40):
            continue
        why = 'read' if tap['kind'] == 'read' else 'copied'
        if why == 'read' and any(l['id'] == tap['id'] and l['why'] == 'copied' for l in learned):
            continue
        learned = [l for l in learned if not (l['id'] == tap['id'] and l['why'] in (why, 'read'))]
        learned.append({'id': tap['id'], 't': text(it), 'at': NOW.isoformat(), 'why': why})
        learned_ids.add(tap['id'])
        today += 1

    base, base_w = load_profile(embed)
    l_emb = load_learned_embeddings(embed, learned)
    l_age = np.array([(NOW - ts(l['at'])).total_seconds() / 86400 for l in learned], dtype=np.float32)
    l_w = np.array([s['learn_weights'].get(l['why'], 0.5) for l in learned], dtype=np.float32) \
        * np.clip(1 - l_age / s['learn_days'], 0.1, 1)
    profile = np.vstack([base, l_emb]) if learned else base
    weights = np.concatenate([base_w, l_w]) if learned else base_w
    prof_ids = [None] * len(base) + [l['id'] for l in learned]

    # 4. score everything still kept against today's profile, rank within the last keep_hours
    ids = [k for k in items if k in emb_store]
    if ids:
        scores = relevance(np.array([emb_store[k] for k in ids]), profile, weights, s['top_k'], ids, prof_ids)
        for k, sc in zip(ids, scores):
            items[k]['score'] = round(float(sc), 4)
    # what the owner removed is gone for everyone; a story very like an 'irrelevant' or 'not news' one stays out
    # too (same language: the model finds any two Arabic headlines rather alike), and near ones score lower
    owner = admin.prune(owner, NOW, s.get('removed_days', 30))
    owner['moved'] = {k: v for k, v in owner['moved'].items() if k in items}
    for it in items.values():
        it.pop('removed', None)
    for r in owner['removed']:
        if r['id'] in items:
            items[r['id']]['removed'] = True
    teach = [r for r in owner['removed'] if r['why'] in admin.LEARN and r['id'] in items]
    if teach and ids:
        r_emb = load_learned_embeddings(embed, [{**r, 'why': 'removed'} for r in teach], STATE / 'removed_emb.npz')
        r_lang = [items[r['id']].get('lang', '') for r in teach]
        sims = np.array([emb_store[k] for k in ids]) @ r_emb.T
        lo, hi = s.get('removed_near', 0.72), s.get('removed_drop', 0.86)
        for k, row in zip(ids, sims):
            j = int(row.argmax())
            if row[j] >= hi and items[k].get('lang', '') == r_lang[j]:
                items[k]['removed'] = True
            elif row[j] >= lo:
                items[k]['score'] = round(float(items[k]['score'] - s.get('removed_penalty', 0.05) * min(1, (row[j] - lo) / (hi - lo))), 4)
    # rank within each language: the model scores some languages (Arabic) higher across the board. The scale is
    # the established sources' own; a source added for its camp (scale: false) is placed on it without moving it
    ref = [k for k in ids if items[k]['source'] not in off_scale] or ids
    ranked = {'': np.sort(np.array([items[k]['score'] for k in ref], dtype=np.float32))}
    for lang in {items[k].get('lang', '') for k in ref}:
        sc = [items[k]['score'] for k in ref if items[k].get('lang', '') == lang]
        if lang and len(sc) >= 50:
            ranked[lang] = np.sort(np.array(sc, dtype=np.float32))
    for k in ids:
        items[k]['pct'] = percentile(ranked.get(items[k].get('lang', ''), ranked['']), items[k]['score'])
        items[k]['gpct'] = percentile(ranked[''], items[k]['score'])  # across all languages

    # 5. same story from several outlets -> one card; many outlets -> "big story"
    # noise (liveblogs, podcasts, sport) never joins a story – as its lead it would hide the whole story
    recent = sorted((k for k in ids if ts(items[k]['found']) >= NOW - timedelta(hours=36) and not is_noise(items[k])),
                    key=lambda k: items[k]['found'])
    for it in items.values():
        alone = it['source'] in channel or it['source'] in movement
        it.update(lead=True, outlets=1, also=[], big=False, important=False, confirmed=0 if alone else 1,
                  _ref_out=1, _ref_est=0 if alone or it['source'] in off_scale else 1, members=[it['id']],
                  camps={camp_of.get(it['source']) or 'ukendt': 1},
                  first={'source': label_of.get(it['source'], it['source']), 'camp': camp_of.get(it['source']) or None,
                         'published': it.get('published')})
        for k in ('cluster_pct', 'cluster_gpct', 'sec', 'secs', 'rank', 'spct', 'cover', 'actors', 'tier', 'tags',
                  'powers', 'method', 'fit', 'live'):
            it.pop(k, None)

    def lead_quality(x):
        """How well this article would lead its story (the owner: informative headlines, never curiosity ones). A
        Danish headline that says the news goes before an English one, which the app would show machine-translated
        until the editor has written his own."""
        q = (fit_of.get(x['source'], 1.0) + (s.get('lead_danish', 0.35) if x.get('lang') == 'da' else 0)
             + (0.1 if x.get('summary') else 0) + x['pct'] / 1000)
        if x.get('lang') in READABLE and curious(x['title']):
            q -= s.get('lead_curious', 0.5)
        return round(q, 4)

    def story(members):
        """One card for the members: a Danish/English article from an established outlet leads when there is
        one (a channel post or a foreign-language article still counts as an outlet); the movement's outlets and
        governments' own channels lead only a story no one else carries, and a source added for its camp's view
        only one the established sources do not carry (the camps show in the coverage). Among the rest the most
        informative headline leads: the source's fit, less for a curiosity headline, a little for a teaser and the
        group's taste."""
        lead = max(members, key=lambda x: (x.get('lang') in READABLE, x['source'] not in movement,
                                           x['source'] not in official, x['source'] not in off_scale,
                                           x['source'] not in channel, lead_quality(x), x['pct'], x['score']))
        outlets = lambda ms: len({outlet_of.get(m['source'], m['source']) for m in ms})
        counted = [m for m in members if m['source'] not in movement]
        n_out = outlets(counted) or 1
        n_est = outlets([m for m in counted if m['source'] not in channel])
        for m in members:
            m.update(lead=m is lead, outlets=n_out, confirmed=n_est, also=[], member=m is not lead)
            m.pop('cluster_pct', None)
            m.pop('cluster_gpct', None)
        # the outlets on the established sources' scale: what the rank and a big story count (scale: false never)
        lead['_ref_out'] = outlets([m for m in counted if m['source'] not in off_scale]) or 1
        lead['_ref_est'] = outlets([m for m in counted if m['source'] not in off_scale and m['source'] not in channel])
        # the other outlets, one article each, taking turns between kinds of media so a story shows how
        # Danish, Western, Arab/Muslim, Israeli and Eastern media, governments and the channels each tell it
        by_kind, seen_outlets = {}, {outlet_of.get(lead['source'], lead['source'])}
        for m in sorted(members, key=lambda x: -x['pct']):
            o = outlet_of.get(m['source'], m['source'])
            if m is not lead and o not in seen_outlets:
                seen_outlets.add(o)
                by_kind.setdefault(group_of.get(m['source'], 'west'), []).append(m)
        kinds = [k for k in KINDS if k in by_kind] + sorted(k for k in by_kind if k not in KINDS)
        others = []
        while len(others) < 10 and any(by_kind.values()):
            for kind in kinds:
                if by_kind[kind] and len(others) < 10:
                    others.append(by_kind[kind].pop(0))
        lead['also'] = [{'id': m['id'], 'source': label_of.get(m['source'], m['source']), 'title': m['title'],
                         'link': m['link'], 'lang': m.get('lang'), 'published': m.get('published'),
                         'group': group_of.get(m['source'], 'west'), 'camp': camp_of.get(m['source']) or None,
                         'title_tr': m.get('title_tr')} for m in others]
        # every member (the story's lasting identity: the editor admits a story by any of them), the camps that
        # carried it and who was first
        lead['members'] = sorted(m['id'] for m in members)
        camps = {}
        for m in members:
            c = camp_of.get(m['source']) or 'ukendt'
            camps[c] = camps.get(c, 0) + 1
        lead['camps'] = camps
        first = min(members, key=lambda x: x.get('published') or x['found'])
        lead['first'] = {'source': label_of.get(first['source'], first['source']),
                         'camp': camp_of.get(first['source']) or None, 'published': first.get('published')}
        lead['cluster_pct'] = max(m['pct'] for m in members)
        lead['cluster_gpct'] = max(m.get('gpct', 0) for m in members)
        return [lead] + [m for m in members if m is not lead]

    stories = []   # each story: its members, the card (lead) first
    if recent:
        emb = np.array([emb_store[k] for k in recent])
        stories = [story([items[recent[i]] for i in g]) for g in
                   clusters(emb, range(len(recent)), s['same_story_similarity'],
                            [items[k].get('lang', '') for k in recent], s.get('same_story_strict', {}),
                            [city_of(items[k]) for k in recent], s.get('same_story_other_city', 1.01))]
        # second look: two cards whose headlines say the same thing (often one Danish, one English) become
        # one story. Only the cards are compared, best story first, so different stories never chain together;
        # Arabic cards are left alone because the model finds all Arabic headlines rather alike.
        stories.sort(key=lambda st: -st[0]['cluster_pct'])
        joined, keys, where = [], [], []
        for st in stories:
            lead = st[0]
            if lead.get('lang') in READABLE and keys:
                sims = np.array(keys) @ emb_store[lead['id']]
                j = int(sims.argmax())
                a, b = city_of(lead), city_of(joined[where[j]][0])
                if sims[j] >= (s.get('same_story_other_city', 1.01) if a and b and not a & b else s['same_story_merge']):
                    joined[where[j]] = story(joined[where[j]] + st)
                    continue
            joined.append(st)
            if lead.get('lang') in READABLE:
                keys.append(emb_store[lead['id']])
                where.append(len(joined) - 1)
        stories = joined
    clustered = {m['id'] for st in stories for m in st}
    stories += [[items[k]] for k in ids if k not in clustered and not items[k].get('member') and not is_noise(items[k])]

    # 6. where each story belongs (Danmark / Mellemøsten / Verden) and how strongly it should rank.
    # The group's taste comes first; then how many outlets carry the story and whether it is about the
    # group's core subjects. Danish politics gets the biggest lift, because the links the group shares are
    # mostly about other countries, so taste alone would bury it.
    sig = {m['id']: sections.signals(m) for st in stories for m in st}
    lead_emb = np.array([emb_store[st[0]['id']] for st in stories]) if stories else np.zeros((0, 384), np.float32)
    placed = sections.place([[{'source': m['source'], 'lang': m.get('lang'), 'sig': sig[m['id']]} for m in st]
                             for st in stories], lead_emb, hint)
    # the brain (method.py): the books' order of importance and the powers by Hizb ut-Tahrir's newest answers weigh
    # every story
    meth = Method(wiki=load(ROOT / 'public' / 'viden' / 'begreber-index.json', None))
    ranks, ranks_ref = {}, {}
    for st, secs in zip(stories, placed):
        lead, ls = st[0], sig[st[0]['id']]
        core = max(sig[m['id']]['core'] for m in st)
        core_dk = max(sig[m['id']]['core_dk'] for m in st) if secs[0] == 'dk' else 0
        est = lead['_ref_est']   # outlets on the established scale (an added camp's outlet confirms, but adds no rank)
        r = lead.get('cluster_pct', lead['pct']) + (s['rank_per_outlet'] * min(est - 1, 5) if est >= 2 else 0)
        if core_dk:   # Danish politics, Islam and Muslims, immigration
            r += s['rank_core_dk'] if core_dk >= 2 else s['rank_core_dk'] / 2
        elif core:
            r += s['rank_core'] if core >= 2 else s['rank_core'] / 2
        # the lead's fit (the most informative outlet the story has, chosen by fit): a small weight, about −5 to +3
        lead['fit'] = fit_of.get(lead['source'], 1.0)
        r += s.get('rank_fit', 0) * (lead['fit'] - 1)
        lead['sec'] = secs[0]
        lead['actors'] = meth.actors(meth.text(lead))
        lead['tier'], lead['tags'], lead['powers'] = meth.weigh(lead, ls['trivia'], lead['actors'])
        # the books' order: the leading state's acts up, ceremony down – a lift only for what an established outlet
        # carries (a channel's post about a summit is no confirmed act)
        up = meth.lift(lead['tier'])
        r += up if up < 0 or lead['confirmed'] else 0
        lift = next(((owner.get('rank') or {})[m['id']]['v'] for m in st if m['id'] in (owner.get('rank') or {})), None)
        if lift:                                      # the owner raised or lowered it in the app
            r += s.get('owner_rank_step', 30) * (1 if lift == 'up' else -1)
        if ls['trivia']:
            r -= s.get('rank_trivia', 30)             # weather, royals, sport, celebrities … (the owner: 30, 2026-10-11)
        if ls['local'] and not core_dk and secs[0] == 'dk':
            r -= 10                                   # everyday crime and accidents
        if not ls['named'] and core < 2:
            r -= 10                                   # a headline that names no place, party or core subject
        cover = {}
        for m in st:
            cover.setdefault(group_of.get(m['source'], 'west'), set()).add(outlet_of.get(m['source'], m['source']))
        for m in st:
            m['sec'] = secs[0]
        lead.update(secs=secs, rank=round(r, 1), cover={g: len(v) for g, v in cover.items()})
        lead['_core'], lead['_core_dk'], lead['_dk_outlets'] = max(core, core_dk), core_dk, len(cover.get('dk', ()))
        if lead['source'] not in wire:   # a lone wire line is no story, so it must not shift the section's bar
            ranks.setdefault(secs[0], []).append(r)
            if any(m['source'] not in off_scale for m in st):   # nor a story only the added camps carry
                ranks_ref.setdefault(secs[0], []).append(r)
    # the owner moved it: the whole story goes to that section
    for st in stories:
        mv = next((owner['moved'][m['id']] for m in st if m['id'] in owner['moved']), None)
        if mv and mv != st[0]['sec']:
            for m in st:
                m['sec'] = mv
            st[0]['secs'] = [mv] + [x for x in st[0]['secs'] if x != mv]
            ranks.setdefault(mv, []).append(st[0]['rank'])
            ranks_ref.setdefault(mv, []).append(st[0]['rank'])
    # each section's bar on the established scale (all its stories while it has hardly any of its own)
    ranks = {k: np.sort(np.array(ranks_ref[k] if len(ranks_ref.get(k, ())) >= 10 else v, dtype=np.float32))
             for k, v in ranks.items()}

    shown, bypassed = [], {}
    for st in sorted(stories, key=lambda st: -st[0]['rank']):
        it = st[0]
        if is_noise(it) or it['source'] in wire:
            continue
        it['spct'] = top_share(ranks[it['sec']], it['rank'])   # place within its own section
        cpct = it.get('cluster_pct', it['pct'])
        # a big story must matter to the group across all languages, so a widely covered but off-topic
        # Danish story (weather, northern lights) never qualifies through the Danish-only ranking …
        gpct = it.get('cluster_gpct', it.get('gpct', 0))
        it['big'] = (it['_ref_out'] >= s['big_story_sources'] and cpct >= s['big_story_min_percentile']
                     and gpct >= s.get('big_story_min_global_percentile', 72))
        # … but a political story most Danish media carry at once is big news in Denmark
        if (it['sec'] == 'dk' and it['_dk_outlets'] >= s['big_dk_outlets'] and it['_core'] >= 2
                and not sig[it['id']]['trivia']):
            it['big'] = True
        it['important'] = it['big'] or it['spct'] >= s['important_percentile']
        if sig[it['id']]['trivia']:   # light news is never big or important, however many front pages carry it
            it['big'] = it['important'] = False
        it['foreign'] = it.get('lang') not in READABLE
        # Danish news has to touch politics, Islam and Muslims or immigration – or be on most Danish front pages
        everyday = (it['sec'] == 'dk' and not it['_core_dk']
                    and (it['_dk_outlets'] < s['big_dk_outlets'] - 1 or sig[it['id']]['trivia']))
        if it['big'] or (it['spct'] >= s['show_percentile'] and it['rank'] >= s['rank_floor'] and not everyday):
            shown.append(it)
        elif (it['tier'] in meth.bypass_tiers and not sig[it['id']]['trivia'] and it['confirmed']
              and it['rank'] >= meth.bypass_floor):
            # below the taste bar, but the books weigh it (the leading state's acts, a coup, the campaign against
            # Islam): the editor must see it – a few a day, the strongest first
            day = int((NOW - ts(it['found'])).total_seconds() // 86400)
            if bypassed.get(day, 0) < meth.bypass_per_day:
                bypassed[day] = bypassed.get(day, 0) + 1
                it['method'] = True
                shown.append(it)
    # balance: one prolific source may fill at most a few important slots per day (big stories exempt),
    # a busy Telegram channel at most a handful of lines per day, and a source added for its camp's view
    # (scale: false) at most a few cards of its own
    per_source, per_channel, per_added, kept = {}, {}, {}, []
    for it in shown:  # already sorted best first
        if it['important'] and not it['big'] and ts(it['found']) >= NOW - timedelta(hours=24):
            per_source[it['source']] = per_source.get(it['source'], 0) + 1
            if per_source[it['source']] > s.get('max_important_per_source', 4):
                it['important'] = False
        if it['source'] in channel and not it['big']:
            day = (it['source'], int((NOW - ts(it['found'])).total_seconds() // 86400))   # per 24 hours back
            per_channel[day] = per_channel.get(day, 0) + 1
            if per_channel[day] > s['max_channel_per_day']:
                continue
        if it['source'] in off_scale and not it['big']:
            day = (it['source'], int((NOW - ts(it['found'])).total_seconds() // 86400))
            per_added[day] = per_added.get(day, 0) + 1
            if per_added[day] > s.get('max_added_per_day', 3):
                continue
        kept.append(it)
    # posts no established outlet carries fill at most about an eighth of a section (they were a quarter of Mellemøsten)
    per_sec = {}
    for it in kept:
        per_sec[it['sec']] = per_sec.get(it['sec'], 0) + 1
    unconfirmed, shown = {}, []
    for it in kept:   # best first
        if not it['confirmed'] and not it['big']:
            unconfirmed[it['sec']] = unconfirmed.get(it['sec'], 0) + 1
            if unconfirmed[it['sec']] > max(4, per_sec[it['sec']] // 8):
                continue
        shown.append(it)
    for it in shown:
        cpct = it.get('cluster_pct', it['pct'])
        if it['big'] and cpct >= s['learn_big_min_percentile'] and it['id'] not in learned_ids:
            learned.append({'id': it['id'], 't': text(it), 'at': NOW.isoformat(), 'why': 'big'})
            learned_ids.add(it['id'])

    # what Live shows (level.py): the editor's level for the day as a rank floor and a soft count for the last 24
    # hours, plus take and drop; a big story and Danish politics on Islam, Muslims, integration and foreign policy are
    # never cut. `shown` stays the whole candidate pool (data.json, for the editor and search); app.json holds the
    # admitted stories
    members_of_lead = {st[0]['id']: st[1:] for st in stories}

    def protect(it):
        if it['big']:
            return 'big'
        danish = [m for m in [it] + members_of_lead.get(it['id'], []) if m.get('lang') == 'da']
        if (it['sec'] == 'dk' and it['confirmed'] and not sig[it['id']]['trivia']
                and (it.get('tier') == 6 or any(sections.protect_dk.hits(m['title']) for m in danish))):
            return 'dk'
        return None
    day_plan = level.plan(live_plan, local_now(s).date().isoformat(), local_now(s).hour, NOW)
    levels = {k: tuple(v) for k, v in s.get('live_levels', {'få': [104, 20], 'normal': [96, 38], 'mange': [88, 72]}).items()}
    on_live, admitted, live_info = level.admit(
        shown, levels, s.get('live_keep_margin', 4), day_plan, admitted, NOW,
        lambda it: ts(it['published'] or it['found']), protect)
    for it in shown:
        it['live'] = on_live.get(it['id'])

    for it in items.values():
        for k in ('_core', '_core_dk', '_dk_outlets', '_ref_out', '_ref_est'):
            it.pop(k, None)

    # foreign-language cards (no Danish/English version of the story): translate to English once,
    # then every card gets a Danish version for the app's "Dansk" setting
    translator = Translator(CACHE)
    for lang in {it['lang'] for it in shown if it['foreign'] and 'title_tr' not in it}:
        todo = [it for it in shown if it['lang'] == lang and it['foreign'] and 'title_tr' not in it]
        titles = translator([it['title'] for it in todo], lang)
        sums = translator([it['summary'] or '' for it in todo], lang)
        for it, t, sm in zip(todo, titles, sums):
            if t:
                it['title_tr'], it['summary_tr'] = t, (sm or '') if it['summary'] else ''
    todo = [it for it in shown if 'title_da' not in it and it['lang'] != 'da' and (it['lang'] == 'en' or it.get('title_tr'))]
    if todo:
        en_title = [military(it.get('title_tr') or it['title']) for it in todo]
        en_sum = [military((it.get('summary_tr') if it['foreign'] else it['summary']) or '') for it in todo]
        for it, t, sm in zip(todo, translator(en_title, 'en', 'da'), translator(en_sum, 'en', 'da')):
            if t:
                it['title_da'], it['summary_da'] = tidy(t), tidy(sm or '')

    for it in shown:  # also tidies translations stored by earlier versions
        if it.get('title_tr'):
            it['title_tr'], it['summary_tr'] = tidy(it['title_tr']), tidy(it.get('summary_tr') or '')
    # the words that say who and where, which the app sets in bold – for each version of the headline
    for it in shown:
        it['kw'] = sections.keywords(it['title']) if it.get('lang') in READABLE else []
        it['kw_tr'] = sections.keywords(it['title_tr']) if it.get('title_tr') else []
        it['kw_da'] = sections.keywords(it['title_da']) if it.get('title_da') else []

    # the other outlets' Arabic and Turkish headlines on shown stories, so the coverage view can show how
    # Arab media tell a story (headlines only; translated once and kept)
    members_of = {st[0]['id']: st[1:] for st in stories}
    foreign_others = [m for it in shown for m in members_of.get(it['id'], [])
                      if m.get('lang') not in READABLE and 'title_tr' not in m]
    for lang in {m['lang'] for m in foreign_others}:
        todo = [m for m in foreign_others if m['lang'] == lang]
        for m, t in zip(todo, translator([m['title'] for m in todo], lang)):
            if t:
                m['title_tr'] = tidy(t)
    for it in shown:
        for a in it.get('also', []):
            if items.get(a.get('id'), {}).get('title_tr'):
                a['title_tr'] = items[a['id']]['title_tr']

    # a small picture for each card: its own feed image, another outlet's, or the article page's share image
    try:
        from radar import thumbs
        telegram = {f['name'] for f in feeds if f.get('type') == 'telegram' and not f.get('official')}
        save(STATE / 'pics.json', thumbs.attach(shown, members_of, telegram, STATE / 't', load(STATE / 'pics.json', {}), NOW))
    except ImportError:   # no Pillow (local test runs): the cards simply have no pictures
        pass
    except Exception as e:  # noqa: BLE001 – pictures are a bonus; the radar must keep running
        print(f'pictures failed: {type(e).__name__}: {e}')

    # one-line statements ("Kremlin: ...") from the wire and elsewhere, for the 'Bevægelser' view and the
    # editor's briefing: English and Danish versions made once and kept
    def kind(v):
        """'w' a wire line, 'c' a channel post or 'h' a headline that is one statement by a named actor"""
        if v['source'] in wire:
            return 'w'
        if STATEMENT.match(v['title']):
            who, words = v['title'].split(':', 1)[0], sig.get(v['id']) or sections.signals(v)
            if len(who.split()) <= 6 and any(sections.lex[k].hits(who) for k in sections.keys):
                if v['source'] in channel:
                    return 'c'
                if max(words['core'], words['core_dk']) >= 2:   # a colon headline counts only on core subjects
                    return 'h'
        return 'h' if v.get('lang') == 'en' and SAYS.match(v['title']) else None
    statements = [v for v in items.values() if ts(v['found']) >= NOW - timedelta(hours=s['lines_hours'])
                  and not is_noise(v) and kind(v)]
    todo = [v for v in statements if v.get('lang') not in READABLE and v.get('tr_v') != TR_VERSION]
    for lang in {v['lang'] for v in todo}:
        part = [v for v in todo if v['lang'] == lang]
        for v, t in zip(part, translator([v['title'] for v in part], lang)):
            if t:
                v.update(title_tr=tidy(t), tr_v=TR_VERSION)
                v.pop('title_da', None)   # made again from the new English below
    todo = [v for v in statements if v.get('lang') != 'da' and 'title_da' not in v
            and (v.get('lang') == 'en' or v.get('title_tr'))]
    for v, t in zip(todo, translator([military(v.get('title_tr') or v['title']) for v in todo], 'en', 'da')):
        if t:
            v['title_da'] = tidy(t)

    # 7. notifications: never twice for the same story, batched, capped, quiet at night
    new_ids = {i['id'] for i in new}
    notified = [n for n in pushes.get('notified', []) if ts(n['at']) >= NOW - timedelta(hours=48) and n['id'] in emb_store]
    told = np.array([emb_store[n['id']] for n in notified]) if notified else np.zeros((0, 384), np.float32)
    pending = [p for p in pushes['pending'] if ts(p['at']) >= NOW - timedelta(hours=3) and p['id'] in emb_store]
    for it in shown:
        why = 'top' if it['id'] in new_ids and it.get('cluster_pct', it['pct']) >= s['notify_percentile'] else 'big' if it['big'] else None
        if not why or first_run or (it['foreign'] and not it.get('title_tr')) or not it['confirmed'] or not it['live']:
            continue   # never for a Telegram/YouTube post no established outlet carries, nor one Live does not show
        e = emb_store[it['id']]
        if len(told) and float((told @ e).max()) >= s['same_story_similarity']:
            continue  # already told about this story
        if any(p['id'] == it['id'] or float(emb_store[p['id']] @ e) >= s['same_story_similarity'] for p in pending):
            continue
        pending.append({'id': it['id'], 'why': why, 'at': NOW.isoformat()})

    gone = set()
    sent_today = [x for x in pushes['sent'] if ts(x) >= NOW - timedelta(hours=24)]
    last = max((ts(x) for x in pushes['sent']), default=None)
    gap_ok = last is None or NOW - last >= timedelta(minutes=s['notify_min_gap_minutes'])
    if pending and gap_ok and not in_quiet_hours(s) and len(sent_today) < s['notify_max_per_day']:
        batch = sorted(pending, key=lambda p: (p['why'] != 'big', -items[p['id']]['pct']))
        lead = items[batch[0]['id']]
        headline = push_headline(lead, ed_titles)
        if len(batch) == 1:
            where = ' i Danmark' if lead.get('sec') == 'dk' else ''
            title = (f"Topnyhed{where} · {lead['outlets']} medier" if lead['big']
                     else label_of.get(lead['source'], lead['source']))
            body = headline
        else:
            title = f'{len(batch)} vigtige nyheder'
            body = f"{headline}  (+{len(batch) - 1} mere)"
        result = push.send({'title': title, 'body': body, 'url': f"./?item={lead['id']}&n=1", 'tag': lead['id']},
                           push.everyone(phones, 'top'))
        print('push:', result)
        gone.update(result.get('gone') or [])
        if result.get('sent'):
            pushes['sent'].append(NOW.isoformat())
            notified += [{'id': p['id'], 'at': NOW.isoformat()} for p in batch]
            pending = []
    # each update of the editor's overview of the day gets its own notification as soon as it appears
    if digest.get('created') and digest['created'] > pushes.get('digest_sent', '') and in_quiet_hours(s):
        pushes['digest_sent'] = digest['created']  # written at night (e.g. a test run): show it, never buzz about it
    if (digest.get('created') and digest['created'] > pushes.get('digest_sent', '')
            and NOW - ts(digest['created']) < timedelta(hours=3)):
        note = digest.get('push') if 'date' in digest else {   # an edition from before the overview of the day
            'title': f"Khabar · overblik {digest.get('period', '')}".strip(),
            'body': digest.get('intro') or (digest.get('items') or [{}])[0].get('headline', '')}
        if note:   # an update that added nothing is no news
            result = push.send({**note, 'url': './?digest=1', 'tag': 'digest'}, push.everyone(phones, 'digest'))
            print('digest push:', result)
            gone.update(result.get('gone') or [])
        pushes['digest_sent'] = digest['created']

    phones = [p for p in phones if p['endpoint'] not in gone]   # app deleted or notifications off: drop the phone
    pushes.update(pending=pending, notified=notified,
                  sent=[x for x in pushes['sent'] if ts(x) >= NOW - timedelta(days=2)])

    # Hizb ut-Tahrir's new political answers (the amir's answers to questions): a layer of their own, never a card
    # and never ranked with the news (analyses.py). The answers the app already holds (movement-index.json) are
    # only listed; the text of a new one is kept for the editor. The cloud run sets RADAR_ANALYSES=1, local and
    # test runs stay offline.
    found_analyses = load(STATE / 'analyses.json', {})
    if os.environ.get('RADAR_ANALYSES') == '1':
        known = set((load(ROOT / 'public' / 'viden' / 'movement-index.json', {}).get('answers') or {}))
        found_analyses = analyses.update(found_analyses, NOW, known=known)
        save(STATE / 'analyses.json', found_analyses)
    # a new answer of Hizb ut-Tahrir's: one notification to the phones that asked for it (pro-plan 5.5), once, never at
    # night (it waits for the morning while it is at most two days old); the answers already there the first time are
    # no news
    if 'svar_sent' not in pushes:
        pushes['svar_sent'] = sorted(x['id'] for x in (found_analyses.get('items') or []))[-200:]
    told_svar = set(pushes['svar_sent'])
    fresh_svar = analyses.to_tell(found_analyses, told_svar, NOW)
    if fresh_svar and not first_run and not in_quiet_hours(s):
        a = fresh_svar[0]
        result = push.send({'title': 'Nyt svar fra Hizb ut-Tahrir', 'body': analyses.push_title(a['title']),
                            'url': f"./?svar={a['id']}&n=1", 'tag': f"svar-{a['id']}"}, push.everyone(phones, 'svar'))
        print('answer push:', result)
        phones = [p for p in phones if p['endpoint'] not in set(result.get('gone') or [])]
        pushes['svar_sent'] = sorted(told_svar | {x['id'] for x in fresh_svar})[-200:]

    # 8. write state + the public files the app reads
    public_fields = ('id', 'title', 'summary', 'link', 'source', 'lang', 'published', 'found',
                     'pct', 'rank', 'spct', 'sec', 'secs', 'big', 'important', 'outlets', 'confirmed', 'cover',
                     'also', 'foreign', 'title_tr', 'summary_tr', 'title_da', 'summary_da', 'thumb', 'pic', 'kw', 'kw_tr', 'kw_da',
                     'members', 'camps', 'first', 'actors', 'tier', 'tags', 'powers', 'method', 'fit', 'live', 'kind')
    app_fields = ('id', 'title', 'summary', 'link', 'lang', 'published', 'found', 'rank', 'sec', 'secs', 'big', 'important',
                  'outlets', 'confirmed', 'cover', 'foreign', 'title_tr', 'summary_tr', 'title_da', 'summary_da', 'thumb',
                  'pic', 'kw', 'kw_tr', 'kw_da', 'actors', 'members', 'live', 'kind')
    also_fields = ('id', 'source', 'title', 'link', 'lang', 'group', 'title_tr')

    def slim(d, keys):   # empty values left out (the app reads a missing field as empty); 0 stays (confirmed: 0)
        return {k: d[k] for k in keys if d.get(k) is not None and d.get(k) is not False and d.get(k) not in ('', [], {})}

    def app_item(it):
        out = slim(it, app_fields)
        if out.get('members') == [it['id']]:
            out.pop('members')   # a story of one article: its id is its only member
        out['source'] = label_of.get(it['source'], it['source'])
        out['group'] = group_of.get(it['source'], 'west')
        if it.get('also'):
            out['also'] = [slim(a, also_fields) for a in it['also']]
        return out

    shown.sort(key=lambda x: x['found'] + x['published'], reverse=True)
    for it in shown:   # commentary is labelled in the app and never leads the editor's front page (pro-plan 3.3)
        it['kind'] = 'kommentar' if commentary(it.get('link'), it.get('title')) else None
    why_count = {w: sum(1 for l in learned if l['why'] == w) for w in s['learn_weights']}
    common = {
        'updated': NOW.isoformat(),
        'sections': sections.names,
        'scanned_24h': sum(1 for v in items.values() if ts(v['found']) >= NOW - timedelta(hours=24)),
        # the movement's new answers the radar has found (titles, dates and links; the text stays in the state)
        'analyses': analyses.for_app(found_analyses),
        # the owner's front-page choices: quote, main story, raised/lowered stories
        'owner': {'quote': (owner.get('quote') or {}).get('key'), 'lead': (owner.get('lead') or {}).get('id'),
                  'rank': {k: v['v'] for k, v in (owner.get('rank') or {}).items()}},
    }
    # the whole candidate pool, for the editor and search: every story with its rank line (`live`: why Live shows it,
    # or null) and the level applied (`live` at the top)
    save(STATE / 'data.json', {
        **common,
        'items': [{**{k: it.get(k) for k in public_fields}, 'source': label_of.get(it['source'], it['source']),
                   'group': group_of.get(it['source'], 'west')} for it in shown],
        'sources': {k: {'ok': v['ok'], 'items': v['items'], 'failing_runs': health.get(k, 0),
                        'group': group_of.get(k, 'west'), 'label': label_of.get(k, k)} for k, v in status.items()},
        'learned': why_count,
        'live': live_info,
    })
    # what the app shows (the owner's rule of 2026-10-17, notes-owner-volume.md): the admitted stories of the last 48
    # hours and every big story, with only the fields the app reads (public/app.js) – a fraction of data.json
    save(STATE / 'app.json', {
        **common,
        'items': [app_item(it) for it in shown if level.in_app(it, day_plan)],   # a big story the editor dropped: out too
        'sources': {k: {'label': label_of.get(k, k), 'group': group_of.get(k, 'west'),
                        **({'failing_runs': health[k]} if health.get(k) else {})} for k in status},
        'live': {'level': live_info['level'], 'n_24h': live_info['n_24h']},
    })
    save(STATE / 'admitted.json', admitted)
    # every wire line of the window (Claude translates them all into 'Bevægelser'), plus the newest other statements
    newest = sorted(statements, key=lambda v: v['published'], reverse=True)
    keep = [v for v in newest if v['source'] in wire] + [v for v in newest if v['source'] not in wire][:300]
    save(STATE / 'lines.json', {'updated': NOW.isoformat(), 'items': [
        {'i': v['id'], 't': v['title'], 'tr': v.get('title_tr'), 'da': v.get('title_da'),
         's': label_of.get(v['source'], v['source']), 'l': v.get('lang'), 'p': v['published'], 'u': v['link'],
         'x': v.get('sec'), 'k': kind(v)}
        for v in sorted(keep, key=lambda v: v['published'], reverse=True)]})
    # everything the radar saw in the last days, for the app's search (loaded only when someone searches)
    on_card = {it['id'] for it in shown}
    save(STATE / 'search.json', {'updated': NOW.isoformat(), 'items': [
        {'i': v['id'], 't': v.get('title_tr') or v['title'], 'da': v.get('title_da'), 's': label_of.get(v['source'], v['source']),
         'l': v.get('lang'), 'u': v['link'],
         'p': v['published'], 'x': v.get('sec'), 'c': int(v['id'] in on_card)}
        for v in sorted(items.values(), key=lambda v: v['published'], reverse=True)
        if not is_noise(v) and (v.get('lang') in READABLE or v.get('title_tr'))
        and ts(v['found']) >= NOW - timedelta(hours=48)][:5000]})
    save(STATE / 'items.json', items)
    save(STATE / 'seen.json', seen)
    save(STATE / 'learned.json', learned)
    save(STATE / 'pushes.json', pushes)
    save(STATE / 'relay.json', relay)
    save(STATE / 'removed.json', owner)
    push.save_phones(STATE / 'phones.bin', os.environ.get('PROFILE_KEY', ''), phones)
    save(STATE / 'health.json', health)
    readers = [x for x in taps if x['kind'] in ('read', 'share') and not x.get('me')]   # the stories read and shared
    stats.update(STATE / 'stats.enc', os.environ.get('ADMIN_KEY', ''), visits + readers, len(push.everyone(phones)), NOW)
    keep = list(emb_store)
    np.savez_compressed(STATE / 'emb.npz', ids=np.array(keep, dtype='U32'),
                        m=np.array([emb_store[k] for k in keep], dtype=np.float16) if keep else np.zeros((0, 384), np.float16))
    bad = [k for k, v in status.items() if not v['ok']]
    print(f"fetched {len(fetched)} · new {len(new)} · kept {len(items)} · shown {len(shown)} · "
          f"live {live_info['n_24h']} in 24 h ({live_info['level']}: {live_info['why']}, line {live_info['line']}) · "
          f"learned {why_count} · owner: {acted} new, {len(owner['removed'])} removed · pending pushes {len(pending)} · failed: {', '.join(bad) or 'none'}")


if __name__ == '__main__':
    main()
