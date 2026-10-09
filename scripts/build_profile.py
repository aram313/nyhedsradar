"""Build the group's taste profile from a WhatsApp chat export.

Every link the group shared becomes one profile line: the text that came with the
link plus the readable words in the article address. The radar later compares new
headlines with these lines. No names are kept.

Usage:  py scripts/build_profile.py <path to _chat.txt> <output .jsonl>
"""
import json
import re
import sys
from urllib.parse import unquote, urlparse

HDR = re.compile(r'^‎?\[(\d\d)\.(\d\d)\.(\d{4}), [\d.]+\] [^:]+?: (.*)$')
URL = re.compile(r'https?://\S+')
SKIP_HOSTS = ('chat.whatsapp.com', 'zoom.us', 'spotify', 'apple.co', 'maps.', 'goo.gl/maps')
NOISE = re.compile(r'(\?|#).*$')


def slug_words(url):
    path = NOISE.sub('', unquote(urlparse(url).path))
    words = re.findall(r'[^\W\d_]{3,}', path.replace('-', ' ').replace('_', ' '))
    words = [w for w in words if len(w) < 18]  # drop id-like blobs
    return ' '.join(words[-14:])


def main(src, out):
    entries, seen = [], set()
    cur = None
    for line in open(src, encoding='utf-8'):
        line = line.rstrip('\n')
        m = HDR.match(line)
        if m:
            if cur:
                entries.append(cur)
            cur = {'d': f'{m[3]}-{m[2]}-{m[1]}', 'text': m[4]}
        elif cur:
            cur['text'] += '\n' + line
    if cur:
        entries.append(cur)

    rows = []
    for e in entries:
        urls = URL.findall(e['text'])
        if not urls:
            continue
        url = urls[0]
        if any(s in url for s in SKIP_HOSTS) or url in seen:
            continue
        seen.add(url)
        text = URL.sub(' ', e['text']).replace('‎', ' ').replace('￼', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        host = (urlparse(url).hostname or '')
        social = any(s in host for s in ('facebook', 'fb.', 'instagram', 'tiktok', 'x.com', 'twitter', 'youtu'))
        words = '' if social else slug_words(url)
        joined = (text[:350] + ' ' + words).strip()
        if len(joined) < 25:
            continue
        rows.append({'d': e['d'], 't': joined})

    with open(out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(rows)} profile lines written')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
