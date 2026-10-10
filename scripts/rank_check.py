"""Try the ranking on real data before changing thresholds or word lists.

Copies the live radar state from the `data` branch into a temporary folder, runs one radar pass there
with no fetching, no new embeddings, no translation and no notifications, and prints what each section
would show. Needs the decrypted profile and its cached embeddings in .cache (profile.jsonl and
profile-*.npz), which are there after any local run.

Usage:  py scripts/rank_check.py [stories per section, default 25]
"""
import contextlib
import io
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import radar.run as run  # noqa: E402

RAW = 'https://raw.githubusercontent.com/aram313/nyhedsradar/data/'
FILES = ['items.json', 'seen.json', 'learned.json', 'pushes.json', 'relay.json', 'health.json', 'emb.npz', 'learned_emb.npz']


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


def main(per_section=25):
    if not list((ROOT / '.cache').glob('profile-*.npz')):
        sys.exit('No cached profile embeddings in .cache – the ranking would be meaningless.')
    state = Path(tempfile.mkdtemp(prefix='khabar-'))
    for name in FILES:
        with urllib.request.urlopen(RAW + name) as r:
            (state / name).write_bytes(r.read())
    run.STATE, run.CACHE = state, ROOT / '.cache'
    run.Embedder, run.Translator = NoNewEmbeddings, NoTranslation
    run.feedback.pull = lambda since: ([], since)
    run.push.send = lambda payload: {'sent': 0}
    run.fetch_all = lambda feeds: ([], {f['name']: {'ok': True, 'items': 0, 'error': None} for f in feeds})
    with contextlib.redirect_stdout(io.StringIO()):
        run.main()
    data = json.loads((state / 'data.json').read_text(encoding='utf-8'))
    out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    for sec, name in data['sections'].items():
        items = sorted((i for i in data['items'] if i['sec'] == sec), key=lambda i: -i['rank'])
        out.write(f"\n{name}: {len(items)} stories ({sum(i['important'] for i in items)} important)\n")
        for i in items[:per_section]:
            mark = 'B' if i['big'] else 'V' if i['important'] else ' '
            out.write(f"  {i['rank']:6.1f} {mark} {i['outlets']:2d} {i['source'][:16]:16s} {i['title'][:90]}\n")
    out.flush()


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 25)
