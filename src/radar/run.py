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

from radar import feedback, push
from radar.translate import Translator, tidy
from radar.feeds import fetch_all

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'config'
STATE = Path(os.environ.get('RADAR_STATE', ROOT / 'state'))
CACHE = Path(os.environ.get('RADAR_CACHE', ROOT / '.cache'))
NOW = datetime.now(timezone.utc)
READABLE = {'da', 'en'}   # languages the owner reads; others are translated or used only as signal


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
                         r'|seneste nyt|\blive blog\b|\bliveblog\b|\blive updates\b', re.I)
NOISE_URL = re.compile(r'/(sport|sports|fodbold|football|soccer|haandbold|cykling|tennis|golf|formel-1|kendte|celebrity|'
                       r'underholdning|entertainment|livsstil|lifestyle|horoskop|vejret|weather|quiz|games|podcasts?|'
                       r'travel|rejser|mad|food|recipes|opskrifter|bolig|motor|biler|tv-guide|musik|music|film-og-serier)(/|-|$)', re.I)


def is_noise(item):
    return bool(NOISE_TITLE.search(item['title'].strip()) or NOISE_URL.search(item['link']))



def norm_title(t):
    return re.sub(r'\W+', ' ', t.lower()).strip()[:90]


def percentile(scores_sorted, s):
    if len(scores_sorted) == 0:
        return 50
    return int(100 * np.searchsorted(scores_sorted, s, side='left') / len(scores_sorted))


def clusters(emb, order, threshold, langs=None, strict=None):
    """Group items about the same story. Each item joins the existing story whose centre it is
    closest to (if close enough), otherwise starts a new one. Comparing with the centre rather
    than with any single member keeps a day of different Gaza stories from melting into one."""
    centres, sums, groups, glang = [], [], [], []
    strict = strict or {}
    for i in order:
        e = emb[i]
        lang = langs[i] if langs else ''
        if centres:
            sims = np.array(centres) @ e
            j = int(sims.argmax())
            # the model rates any two texts in some languages (Arabic) as rather alike,
            # so a story made only of such texts needs a closer match
            need = strict.get(lang, threshold) if glang[j] == {lang} else threshold
            if sims[j] >= need:
                glang[j].add(lang)
                groups[j].append(i)
                sums[j] = sums[j] + e
                centres[j] = sums[j] / np.linalg.norm(sums[j])
                continue
        centres.append(e.copy()); sums.append(e.copy()); groups.append([i]); glang.append({lang})
    return groups


def load_learned_embeddings(embed, learned):
    """Embeddings of self-learned entries, cached between runs so each is computed once."""
    path = STATE / 'learned_emb.npz'
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


def in_quiet_hours(settings):
    start, end = settings['quiet_hours']
    try:
        h = NOW.astimezone(ZoneInfo(settings['timezone'])).hour
    except Exception:  # no time zone database (plain Windows): Danish summer/winter time by EU rule
        def last_sunday(month):
            d = datetime(NOW.year, month, 31, 1, tzinfo=timezone.utc)
            return d - timedelta(days=(d.weekday() + 1) % 7)
        h = (NOW + timedelta(hours=2 if last_sunday(3) <= NOW < last_sunday(10) else 1)).hour
    return h >= start or h < end if start > end else start <= h < end


# ------------------------------------------------------------------ main

def main():
    s = load(CONFIG / 'settings.json', {})
    feeds = load(CONFIG / 'feeds.json', [])
    outlet_of = {f['name']: f.get('outlet', f['name']) for f in feeds}
    max_age = {f['name']: f.get('max_age_hours', s['max_age_hours']) for f in feeds}
    community = {f['name'] for f in feeds if f.get('community')}
    # Telegram and YouTube channels are fast but unverified; everything else is an established outlet
    channel = {f['name'] for f in feeds if f.get('type') in ('telegram', 'youtube')}

    items = load(STATE / 'items.json', {})          # id -> every scored item from the last keep_hours
    seen = load(STATE / 'seen.json', {})            # id -> first seen; stops dropped items coming back
    learned = load(STATE / 'learned.json', [])      # what the radar taught itself: {id, t, at, why}
    pushes = load(STATE / 'pushes.json', {'sent': [], 'pending': [], 'notified': []})
    relay = load(STATE / 'relay.json', {'since': None})
    health = load(STATE / 'health.json', {})        # source -> runs in a row it failed
    digest = load(os.environ.get('RADAR_DIGEST', CACHE / 'digest.json'), {})  # written by the Claude editor
    emb_store = {}
    if (STATE / 'emb.npz').exists():
        z = np.load(STATE / 'emb.npz', allow_pickle=False)
        emb_store = dict(zip(z['ids'].tolist(), z['m'].astype(np.float32)))
    first_run = len(items) < 300

    fetched, status = fetch_all(feeds)
    health = {name: 0 if st['ok'] else health.get(name, 0) + 1 for name, st in status.items()}

    # 1. keep fresh, unseen, de-duplicated items (same link, or same headline from two feeds)
    known_titles = {norm_title(i['title']) for i in items.values()}
    new = []
    for it in fetched:
        pub = ts(it['published']) if it['published'] else NOW
        if pub > NOW + timedelta(hours=1) or NOW - pub > timedelta(hours=max_age.get(it['source'], 48)):
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
    for it in new:
        if it['community'] and it['id'] not in learned_ids:
            learned.append({'id': it['id'], 't': text(it), 'at': it['found'], 'why': 'community'})
            learned_ids.add(it['id'])
    taps, relay['since'] = feedback.pull(relay['since'])
    for tap in taps:
        learned = [l for l in learned if not (l['id'] == tap['id'] and l['why'] == 'copied')]
        learned.append({'id': tap['id'], 't': f"{tap['title']}. {tap['summary'][:220]}", 'at': NOW.isoformat(), 'why': 'copied'})
        learned_ids.add(tap['id'])

    base, base_w = load_profile(embed)
    l_emb = load_learned_embeddings(embed, learned)
    l_age = np.array([(NOW - ts(l['at'])).total_seconds() / 86400 for l in learned], dtype=np.float32)
    l_w = np.array([s['learn_weights'][l['why']] for l in learned], dtype=np.float32) \
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
    # rank within each language: the model scores some languages (Arabic) higher across the board
    ranked = {'': np.sort(np.array([items[k]['score'] for k in ids], dtype=np.float32))}
    for lang in {items[k].get('lang', '') for k in ids}:
        sc = [items[k]['score'] for k in ids if items[k].get('lang', '') == lang]
        if lang and len(sc) >= 50:
            ranked[lang] = np.sort(np.array(sc, dtype=np.float32))
    for k in ids:
        items[k]['pct'] = percentile(ranked.get(items[k].get('lang', ''), ranked['']), items[k]['score'])

    # 5. same story from several outlets -> one card; many outlets -> "big story"
    recent = sorted((k for k in ids if ts(items[k]['found']) >= NOW - timedelta(hours=36)),
                    key=lambda k: items[k]['found'])
    for it in items.values():
        it.update(lead=True, outlets=1, also=[], big=False, important=False,
                  confirmed=0 if it['source'] in channel else 1)
        it.pop('cluster_pct', None)
    if recent:
        emb = np.array([emb_store[k] for k in recent])
        for g in clusters(emb, range(len(recent)), s['same_story_similarity'],
                          [items[k].get('lang', '') for k in recent], s.get('same_story_strict', {})):
            members = [items[recent[i]] for i in g]
            # prefer a Danish/English article as the card; foreign ones still count as outlets
            lead = max(members, key=lambda x: (x.get('lang') in READABLE, x['pct'], x['score']))
            n_out = len({outlet_of.get(m['source'], m['source']) for m in members})
            n_est = len({outlet_of.get(m['source'], m['source']) for m in members if m['source'] not in channel})
            for m in members:
                m['lead'] = m is lead
                m['outlets'] = n_out
                m['confirmed'] = n_est
            lead['also'] = [{'source': m['source'], 'title': m['title'], 'link': m['link']}
                            for m in sorted(members, key=lambda x: -x['pct']) if m is not lead][:8]
            lead['cluster_pct'] = max(m['pct'] for m in members)

    shown = []
    for it in sorted(items.values(), key=lambda x: -x.get('cluster_pct', x.get('pct', 0))):
        if not it['lead'] or 'pct' not in it or is_noise(it):
            continue
        cpct = it.get('cluster_pct', it['pct'])
        it['big'] = it['outlets'] >= s['big_story_sources'] and cpct >= s['big_story_min_percentile']
        it['important'] = it['big'] or cpct >= s['important_percentile']
        it['foreign'] = it.get('lang') not in READABLE
        if cpct >= s['show_percentile'] or it['big']:
            shown.append(it)
    # balance: one prolific source may fill at most a few 'Vigtigste' slots per day (big stories exempt)
    per_source = {}
    for it in shown:  # already sorted best first
        if it['important'] and not it['big'] and ts(it['found']) >= NOW - timedelta(hours=24):
            per_source[it['source']] = per_source.get(it['source'], 0) + 1
            if per_source[it['source']] > s.get('max_important_per_source', 4):
                it['important'] = False
    for it in shown:
        cpct = it.get('cluster_pct', it['pct'])
        if it['big'] and cpct >= s['learn_big_min_percentile'] and it['id'] not in learned_ids:
            learned.append({'id': it['id'], 't': text(it), 'at': NOW.isoformat(), 'why': 'big'})
            learned_ids.add(it['id'])

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
        en_title = [it.get('title_tr') or it['title'] for it in todo]
        en_sum = [(it.get('summary_tr') if it['foreign'] else it['summary']) or '' for it in todo]
        for it, t, sm in zip(todo, translator(en_title, 'en', 'da'), translator(en_sum, 'en', 'da')):
            if t:
                it['title_da'], it['summary_da'] = tidy(t), tidy(sm or '')

    for it in shown:  # also tidies translations stored by earlier versions
        if it.get('title_tr'):
            it['title_tr'], it['summary_tr'] = tidy(it['title_tr']), tidy(it.get('summary_tr') or '')

    # 6. notifications: never twice for the same story, batched, capped, quiet at night
    new_ids = {i['id'] for i in new}
    notified = [n for n in pushes.get('notified', []) if ts(n['at']) >= NOW - timedelta(hours=48) and n['id'] in emb_store]
    told = np.array([emb_store[n['id']] for n in notified]) if notified else np.zeros((0, 384), np.float32)
    pending = [p for p in pushes['pending'] if ts(p['at']) >= NOW - timedelta(hours=3) and p['id'] in emb_store]
    for it in shown:
        why = 'top' if it['id'] in new_ids and it.get('cluster_pct', it['pct']) >= s['notify_percentile'] else 'big' if it['big'] else None
        if not why or first_run or (it['foreign'] and not it.get('title_tr')):
            continue
        e = emb_store[it['id']]
        if len(told) and float((told @ e).max()) >= s['same_story_similarity']:
            continue  # already told about this story
        if any(p['id'] == it['id'] or float(emb_store[p['id']] @ e) >= s['same_story_similarity'] for p in pending):
            continue
        pending.append({'id': it['id'], 'why': why, 'at': NOW.isoformat()})

    sent_today = [x for x in pushes['sent'] if ts(x) >= NOW - timedelta(hours=24)]
    last = max((ts(x) for x in pushes['sent']), default=None)
    gap_ok = last is None or NOW - last >= timedelta(minutes=s['notify_min_gap_minutes'])
    if pending and gap_ok and not in_quiet_hours(s) and len(sent_today) < s['notify_max_per_day']:
        batch = sorted(pending, key=lambda p: (p['why'] != 'big', -items[p['id']]['pct']))
        lead = items[batch[0]['id']]
        headline = lead.get('title_tr') or lead['title']
        if len(batch) == 1:
            title = f"Stor historie · {lead['outlets']} medier" if lead['big'] else lead['source']
            body = headline
        else:
            title = f'{len(batch)} vigtige nyheder'
            body = f"{headline}  (+{len(batch) - 1} mere)"
        result = push.send({'title': title, 'body': body, 'url': f"./?item={lead['id']}", 'tag': lead['id']})
        print('push:', result)
        if result.get('sent'):
            pushes['sent'].append(NOW.isoformat())
            notified += [{'id': p['id'], 'at': NOW.isoformat()} for p in batch]
            pending = []
    # the editor's daily overview gets its own notification as soon as it appears
    if digest.get('created') and digest['created'] > pushes.get('digest_sent', '')             and NOW - ts(digest['created']) < timedelta(hours=3) and not in_quiet_hours(s):
        first = (digest.get('items') or [{}])[0].get('headline', '')
        result = push.send({'title': f"Dagens overblik · {digest.get('period', '')}".strip(' ·'),
                            'body': digest.get('intro') or first, 'url': './?digest=1', 'tag': 'digest'})
        print('digest push:', result)
        pushes['digest_sent'] = digest['created']

    pushes.update(pending=pending, notified=notified,
                  sent=[x for x in pushes['sent'] if ts(x) >= NOW - timedelta(days=2)])

    # 7. write state + the public file the app reads
    public_fields = ('id', 'title', 'summary', 'link', 'source', 'lang', 'published', 'found',
                     'pct', 'big', 'important', 'outlets', 'confirmed', 'also', 'foreign',
                     'title_tr', 'summary_tr', 'title_da', 'summary_da')
    shown.sort(key=lambda x: x['found'] + x['published'], reverse=True)
    why_count = {w: sum(1 for l in learned if l['why'] == w) for w in s['learn_weights']}
    save(STATE / 'data.json', {
        'updated': NOW.isoformat(),
        'items': [{k: it.get(k) for k in public_fields} for it in shown],
        'sources': {k: {'ok': v['ok'], 'items': v['items'], 'failing_runs': health.get(k, 0)} for k, v in status.items()},
        'scanned_24h': sum(1 for v in items.values() if ts(v['found']) >= NOW - timedelta(hours=24)),
        'learned': why_count,
    })
    save(STATE / 'items.json', items)
    save(STATE / 'seen.json', seen)
    save(STATE / 'learned.json', learned)
    save(STATE / 'pushes.json', pushes)
    save(STATE / 'relay.json', relay)
    save(STATE / 'health.json', health)
    keep = list(emb_store)
    np.savez_compressed(STATE / 'emb.npz', ids=np.array(keep, dtype='U32'),
                        m=np.array([emb_store[k] for k in keep], dtype=np.float16) if keep else np.zeros((0, 384), np.float16))
    bad = [k for k, v in status.items() if not v['ok']]
    print(f"fetched {len(fetched)} · new {len(new)} · kept {len(items)} · shown {len(shown)} · "
          f"learned {why_count} · pending pushes {len(pending)} · failed: {', '.join(bad) or 'none'}")


if __name__ == '__main__':
    main()
