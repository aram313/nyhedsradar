"""The answers' whole English text for the answer reader (the owner, 17/10: "kan vi få hele teksten fra analyser ind på
side? som man kan åbne, det skal være på engelsk" – and, asked, to publish the texts as they are).

Reads the local movement corpus (.cache/movement/corpus.json, built from the HT archive; its English texts are files of
E:/Alpha/projects/ht-archive, read only) and writes, for every answer of public/viden/movement-index.json that has an
English text, public/viden/svar-en/<nr>.json = {nr, title, url, text}, plus public/viden/svar-en/index.json listing the
answers that have one. The text is the movement's own, unchanged but for the heading lines at its top. The app fetches a
file only when a reader opens the text.

    py scripts/build_fulltext.py
"""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / '.cache' / 'movement' / 'corpus.json'
INDEX = ROOT / 'public' / 'viden' / 'movement-index.json'
OUT = ROOT / 'public' / 'viden' / 'svar-en'
HEADING = re.compile(r'^(?:updated\s+)?(?:ameer\W*s\s+)?(?:q\s*&\s*a|answer to (?:a )?questions?|questions? and answers?)\s*:?$',
                     re.I)


def parsed(v):
    if isinstance(v, str):
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return None
    return v


def numbers(entry):
    """The article numbers an entry is known by: its Arabic and its English page's."""
    en = parsed(entry.get('en')) or {}
    for u in [*(parsed(entry.get('urls_ar')) or []), en.get('url')]:
        m = re.search(r'/(\d+)\.html', u or '')
        if m:
            yield m.group(1)


def clean(text, title):
    """The text without the heading lines at its top ('Question and Answer', the title itself)."""
    norm = lambda s: re.sub(r'[^\w]+', ' ', s.lower()).strip()  # noqa: E731
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text.replace('\r\n', '\n')) if b.strip()]
    while blocks and len(blocks[0]) < 200 and (HEADING.match(blocks[0]) or norm(blocks[0]) == norm(title or '')
                                               or norm(blocks[0]) in norm(title or '')):
        blocks.pop(0)
    return '\n\n'.join(blocks)


def main():
    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))
    answers = json.loads(INDEX.read_text(encoding='utf-8'))['answers']
    by = {}
    for entry in corpus:
        for n in numbers(entry):
            by.setdefault(n, entry)
    OUT.mkdir(parents=True, exist_ok=True)
    have = []
    for nr in answers:
        entry = by.get(nr)
        en = parsed(entry.get('en')) if entry else None
        path = Path(en['text']) if en and en.get('text') else None
        if not path or not path.exists():
            continue
        text = clean(path.read_text(encoding='utf-8', errors='replace'), en.get('title'))
        if len(text) < 200:
            continue
        (OUT / f'{nr}.json').write_text(json.dumps({'nr': nr, 'title': en.get('title') or '', 'url': en.get('url') or '',
                                                    'text': text}, ensure_ascii=False), encoding='utf-8')
        have.append(nr)
    (OUT / 'index.json').write_text(json.dumps({'nrs': sorted(have, key=lambda n: answers[n]['date'], reverse=True)},
                                               ensure_ascii=False), encoding='utf-8')
    print(f'{len(have)} of {len(answers)} answers have their English text')


if __name__ == '__main__':
    main()
