"""What the articles of the day's great stories say in numbers (the owner, 18/10, on DR's overview of France's riots: 'Se
kilderne her, hvorfor kan vi ikke bruge de samme?' – DR's box gave 550.000 demonstrators according to the authorities and
800.000 according to the organisers, 110 marches, citing Reuters, the interior ministry, the government and the CGT;
Khabar's editor has no internet and saw only the outlets' headlines and teasers).

For the most widely carried stories in Live the radar reads their outlets' article pages (a Google News link resolved
to the outlet's own address, radar/fresh.py) and keeps, for each article, the few sentences that carry a count, with
the outlet: the material from which the editor builds an event page's fact boxes and article (scripts/events.py
grounds every number in them too). Only single sentences, never an article; the app shows none of it. A page is read
once and remembered for KEEP_DAYS. Stdlib only."""
import html
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

READ_STORIES = 10    # the most widely carried stories in Live whose articles are read
READ_LEAST = 6       # outlets a story needs for it
READ_EACH = 6        # its articles read
READ_PAGES = 36      # pages fetched in a run (the rest the next runs)
READ_SECONDS = 25
SENTENCES = 6        # sentences kept from an article
PLACE_SENTENCES = 2  # and the sentences that name the places, for the page's map (the owner, 18/10: 'Er det meningen at
                     # kortet kun viser paris?' – the cities were in the articles, but in sentences without a count)
SENTENCE = 300       # characters a sentence at most
KEEP_DAYS = 2
READ_V = 2           # what a reading keeps: 2 since the place sentences (18/10)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml'}
NO_READ = re.compile(r'^https?://(?:[\w-]+\.)?(?:t\.me|youtube\.com|youtu\.be|x\.com|twitter\.com|facebook\.com)/', re.I)
GOOGLE = re.compile(r'^https?://news\.google\.com/', re.I)
LD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
PARA = re.compile(r'<p\b[^>]*>(.*?)</p>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
NUMBER = re.compile(r'\d+(?:[.,\s]\d{3})*(?:[.,]\d+)?')
MONTHS = ('januar|februar|marts|april|maj|juni|juli|august|september|oktober|november|december|january|february|march|'
          'may|june|july|october')
NOT_A_COUNT = re.compile(r'\b\d{1,2}\.?\s*(?:' + MONTHS + r')\b|\b(?:' + MONTHS + r')\s+\d{1,2}\b|\b\d{1,2}/\d{1,2}\b'
                         r'|\b(?:19|20)\d{2}\b|\b\d{1,2}[.:]\d{2}\b', re.I)


def get(url, limit=600_000, timeout=8):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read(limit).decode('utf-8', 'replace')


def body(page):
    """An article page's text: its structured data's articleBody when it has one, else its paragraphs of some length."""
    for raw in LD.findall(page or ''):
        try:
            d = json.loads(raw.strip())
        except ValueError:
            continue
        for x in d if isinstance(d, list) else [d, *(d.get('@graph') or [])] if isinstance(d, dict) else []:
            if isinstance(x, dict) and isinstance(x.get('articleBody'), str) and len(x['articleBody']) > 200:
                return x['articleBody']
    paras = (re.sub(r'\s+', ' ', html.unescape(TAG.sub(' ', p))).strip() for p in PARA.findall(page or ''))
    return ' '.join(p for p in paras if len(p) >= 60)


# a list of places: a preposition, then two names or more ('in Paris, Lyon and Marseille', 'i blandt andet Nantes, Rennes')
PLACES = re.compile(r"\b(?:in|i|across|throughout|including|such as|cities of|towns of|blandt andet|bl\.a\.|herunder|byer som|"
                    r"byerne)\s+(?:[a-zæøå]+\s+){0,3}[A-ZÆØÅÀ-Ý][\w’'-]+(?:,\s*(?:and\s+|og\s+)?[A-ZÆØÅÀ-Ý][\w’'-]+|\s+(?:and|og)\s+"
                    r"[A-ZÆØÅÀ-Ý][\w’'-]+)+")


def counts(sentence):
    """Whether a sentence carries a count: a number of two digits or more that is not a date, a year or a clock time."""
    return any(len(re.sub(r'\D', '', m)) >= 2 for m in NUMBER.findall(NOT_A_COUNT.sub(' ', sentence)))


def sentences(text, most=SENTENCES, places=PLACE_SENTENCES):
    """The first sentences of a text that carry a count, each once – and the first that list places."""
    text = re.sub(r'\s+', ' ', html.unescape(TAG.sub(' ', text or ''))).strip()
    out, named = [], []
    for s in re.split(r'(?<=[.!?])\s+(?=[\"“«»A-ZÆØÅÀ-Ý\d])', text):
        s = s.strip()
        if not 40 <= len(s) <= SENTENCE or s in out or s in named:
            continue
        if counts(s):
            if len(out) < most:
                out.append(s)
        elif PLACES.search(s) and len(named) < places:
            named.append(s)
        if len(out) >= most and len(named) >= places:
            break
    return out + named


def own_address(link, resolved, resolve):
    """The outlet's own address of a link (a Google News link resolved, and remembered), or None."""
    if not GOOGLE.match(link):
        return link
    if link not in resolved:
        try:
            resolved[link] = resolve(link) or ''
        except Exception:  # noqa: BLE001 – Google said nothing: not this run
            return None
    return resolved[link] or None


def attach(cards, members_of, memory, now, resolve=None, fetch=None):
    """Give the most widely carried stories in Live their articles' count sentences: card['said'] = [{'s': outlet,
    't': sentence}]. memory: {'read': {link: [when, [sentences]]}, 'own': {google link: address}}, kept between runs."""
    if resolve is None:
        from . import fresh
        resolve = fresh.resolve
    fetch = fetch or get
    since = (now - timedelta(days=KEEP_DAYS)).isoformat()
    # pages read before the place sentences were kept (READ_V) are read again
    read = {k: v for k, v in (memory.get('read') or {}).items() if v[0] >= since} if memory.get('v') == READ_V else {}
    resolved = dict(memory.get('own') or {})
    start = time.monotonic()
    great = sorted((c for c in cards if c.get('live') and (c.get('outlets') or 1) >= READ_LEAST),
                   key=lambda c: -(c.get('outlets') or 1))[:READ_STORIES]
    arts = {c['id']: [m for m in [c, *members_of.get(c['id'], [])] if m.get('link') and not NO_READ.match(m['link'])][:READ_EACH]
            for c in great}
    todo = list(dict.fromkeys(m['link'] for ms in arts.values() for m in ms if m['link'] not in read))[:READ_PAGES]

    def one(link):
        if time.monotonic() - start > READ_SECONDS:
            return link, None
        try:
            url = own_address(link, resolved, resolve)
            if not url or NO_READ.match(url):
                return link, []
            return link, sentences(body(fetch(url)))
        except Exception:  # noqa: BLE001 – paywall, block or timeout: nothing from this page
            return link, []
    with ThreadPoolExecutor(8) as pool:
        for link, got in pool.map(one, todo):
            if got is not None:
                read[link] = [now.isoformat(), got]
    for c in cards:
        c.pop('said', None)
    for c in great:
        said, seen = [], set()
        for m in arts[c['id']]:
            for t in (read.get(m['link']) or [None, []])[1]:
                if t not in seen:
                    seen.add(t)
                    said.append({'s': m.get('source') or '', 't': t})
        if said:
            c['said'] = said[:24]
    asked = {m['link'] for ms in arts.values() for m in ms}
    return {'v': READ_V, 'read': {k: v for k, v in read.items() if k in asked or v[1]},
            'own': {k: v for k, v in resolved.items() if k in asked}}

