"""Try the ranking on real data before changing thresholds, word lists or the method.

Copies the live radar state from the `data` branch into a temporary folder, runs one radar pass there
with no fetching, no new embeddings, no translation and no notifications, and prints what Live would show
(one list, all sections, by rank – the app's 'Vigtigste'), the method's tiers and what reached the editor only
through the method, and what each section would show. Needs the decrypted profile and its cached embeddings in
.cache (profile.jsonl and profile-*.npz), which are there after any local run.

Usage:  py scripts/rank_check.py [stories per list, default 25]
        RANK_CHECK_OUT=<folder>    also keep the pass's data.json, lines.json and analyses.json there (a preview of
                                   the app on today's real data)
        RANK_CHECK_STATE=<folder>  read the state from a saved copy instead of the data branch (the same snapshot
                                   for a before/after comparison; the pass runs at the snapshot's own time)
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import radar.run as run  # noqa: E402

RAW = 'https://raw.githubusercontent.com/aram313/nyhedsradar/data/'
FILES = ['items.json', 'seen.json', 'learned.json', 'pushes.json', 'relay.json', 'health.json', 'emb.npz', 'learned_emb.npz']
OPTIONAL = ['removed.json', 'analyses.json']   # the owner's removals apply as in the app; the movement's new answers
KEEP = ['data.json', 'lines.json', 'analyses.json']


class NoNewEmbeddings:
    def __init__(self, model=None):
        pass

    def __call__(self, texts):
        return np.zeros((len(texts), 384), dtype=np.float32)


class NoTranslation:
    def __init__(self, cache_dir):
        pass

    def __call__(self, texts, lang, to='en'):
        return ['' for _ in texts]


def profile_cache():
    """A folder holding a profile and its embeddings. The current profile is used when its embeddings
    are cached; otherwise the newest earlier snapshot (profile-<hash>.jsonl next to profile-<hash>.npz)."""
    import hashlib
    cache = ROOT / '.cache'
    current = cache / 'profile.jsonl'
    if current.exists() and (cache / f"profile-{hashlib.sha1(current.read_bytes()).hexdigest()[:12]}.npz").exists():
        return cache
    pairs = sorted((p for p in cache.glob('profile-*.jsonl') if p.with_suffix('.npz').exists()),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not pairs:
        sys.exit('No cached profile embeddings in .cache – the ranking would be meaningless.')
    tmp = Path(tempfile.mkdtemp(prefix='khabar-profile-'))
    shutil.copy(pairs[0], tmp / 'profile.jsonl')
    shutil.copy(pairs[0].with_suffix('.npz'), tmp / pairs[0].with_suffix('.npz').name)
    print(f'(using the earlier profile snapshot {pairs[0].name}; taste is close to, not exactly, today\'s)')
    return tmp


def main(per_list=25):
    cache = profile_cache()
    state = Path(tempfile.mkdtemp(prefix='khabar-'))
    try:
        check(cache, state, per_list)
    finally:   # the copies hold the plain group profile and the radar state: never leave them behind
        shutil.rmtree(state, ignore_errors=True)
        if cache != ROOT / '.cache':
            shutil.rmtree(cache, ignore_errors=True)


def fetch_state(state):
    saved = os.environ.get('RANK_CHECK_STATE')
    if saved:
        for name in FILES + OPTIONAL:
            if (Path(saved) / name).exists():
                shutil.copy(Path(saved) / name, state / name)
        data = Path(saved) / 'data.json'
        if data.exists():   # the snapshot's own time, so 'the last 24 hours' are the snapshot's
            run.NOW = datetime.fromisoformat(json.loads(data.read_text(encoding='utf-8'))['updated'])
        return
    for name in FILES + OPTIONAL:
        try:
            with urllib.request.urlopen(RAW + name) as r:
                (state / name).write_bytes(r.read())
        except urllib.error.HTTPError:
            if name not in OPTIONAL:
                raise


def check(cache, state, per_list):
    fetch_state(state)
    run.STATE, run.CACHE = state, cache
    run.Embedder, run.Translator = NoNewEmbeddings, NoTranslation
    run.feedback.pull = lambda since: ([], since)
    run.push.send = lambda payload, *phones, **kw: {'sent': 0}
    run.fetch_all = lambda feeds: ([], {f['name']: {'ok': True, 'items': 0, 'error': None} for f in feeds})
    with contextlib.redirect_stdout(io.StringIO()):
        run.main()
    data = json.loads((state / 'data.json').read_text(encoding='utf-8'))
    out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    keep = os.environ.get('RANK_CHECK_OUT')
    if keep:
        Path(keep).mkdir(parents=True, exist_ok=True)
        for name in KEEP:
            if (state / name).exists():
                shutil.copy(state / name, Path(keep) / name)
        out.write(f"(kept {', '.join(n for n in KEEP if (state / n).exists())} in {keep})\n")

    def mark(i):
        return 'B' if i['big'] else 'M' if i.get('method') else 'V' if i['important'] else ' '

    def line(i):
        return (f"  {i['rank']:6.1f} {mark(i)} {i['sec']:5s} t{i.get('tier') or 0:<2d} {i['outlets']:2d} "
                f"{i['source'][:16]:16s} {(i.get('title_da') or i.get('title_tr') or i['title'])[:90]}\n")

    now = datetime.fromisoformat(data['updated'])
    day = [i for i in data['items'] if now - datetime.fromisoformat(i['published'] or i['found']) <= timedelta(hours=24)]
    tiers = Counter(i.get('tier') for i in data['items'])
    method = [i for i in data['items'] if i.get('method')]
    per_sec = ', '.join(f"{n} {data['sections'].get(s, s)}" for s, n in Counter(i['sec'] for i in day).most_common())
    out.write(f"shown {len(data['items'])} · last 24 hours {len(day)} ({per_sec})\n")
    out.write(f"tiers (the books' order, 1 heaviest): {dict(sorted(tiers.items(), key=lambda x: (x[0] is None, x[0] or 0)))}"
              f" · through the method only: {len(method)}\n")
    for i in sorted(method, key=lambda i: (i['tier'], -i['rank']))[:15]:
        out.write(f"  method{line(i)}")
    live = sorted(day, key=lambda i: -i['rank'])
    out.write(f"\nLive, Vigtigste (one list, the last 24 hours by rank): {len(live)} stories\n")
    for i in live[:per_list]:
        out.write(line(i))
    for sec, name in data['sections'].items():
        items = sorted((i for i in data['items'] if i['sec'] == sec), key=lambda i: -i['rank'])
        out.write(f"\n{name}: {len(items)} stories ({sum(i['important'] for i in items)} important)\n")
        for i in items[:per_list]:
            out.write(line(i))
    out.flush()


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 25)
