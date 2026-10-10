"""Fetch and parse news feeds (RSS 2.0, RSS 1.0/RDF and Atom) with the standard library only."""
import gzip
import hashlib
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
TAG = re.compile(r'<[^>]+>')
SPACE = re.compile(r'\s+')


def _local(tag):
    return tag.rsplit('}', 1)[-1].lower()


def _child(el, *names):
    for c in el:
        if _local(c.tag) in names:
            return c
    return None


def _text(el, *names):
    c = _child(el, *names)
    return (c.text or '').strip() if c is not None and c.text else ''


IMG_EXT = re.compile(r'\.(?:jpe?g|png|webp)(?:[?#]|$)', re.I)
IMG_TAG = re.compile(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', re.I)


def image(el):
    """The item's own picture: the widest media:thumbnail, image media:content or image enclosure, else the
    first <img> in its HTML. Empty when the feed has none (the radar may then use the article page's image)."""
    found = []
    for c in el.iter():
        name, url, kind = _local(c.tag), c.get('url') or '', c.get('type') or ''
        if not url.startswith('http'):
            continue
        if (name == 'thumbnail' or (name == 'content' and (c.get('medium') == 'image' or kind.startswith('image/')
                                                         or (not kind and not c.get('medium') and IMG_EXT.search(url))))
                or (name == 'enclosure' and kind.startswith('image/'))):
            try:
                width = int(c.get('width') or 600)
            except ValueError:
                width = 600
            found.append((min(width, 1000), url))
    if found:
        return max(found)[1]
    for name in ('encoded', 'description', 'summary'):
        c = _child(el, name)
        m = IMG_TAG.search(html.unescape(c.text)) if c is not None and c.text else None
        if m:
            return html.unescape(m.group(1))
    return ''


INVISIBLE = re.compile(r'[​-‏⁠﻿]')   # zero-width marks some feeds put between words


def clean(s, limit=None):
    s = html.unescape(TAG.sub(' ', html.unescape(s or '')))
    s = SPACE.sub(' ', INVISIBLE.sub('', s)).strip()
    if limit and len(s) > limit:
        s = s[:limit].rsplit(' ', 1)[0] + ' …'
    return s


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        d = None
    if d is None:
        try:
            d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def parse(xml_bytes, feed):
    root = ET.fromstring(xml_bytes)
    items = []
    for el in root.iter():
        kind = _local(el.tag)
        if kind not in ('item', 'entry'):
            continue
        title = clean(_text(el, 'title'), 300)
        link = _text(el, 'link')
        if not link:
            for c in el:
                if _local(c.tag) == 'link' and c.get('rel', 'alternate') == 'alternate' and c.get('href'):
                    link = c.get('href')
                    break
        if not title or not link:
            continue
        summary = clean(_text(el, 'description', 'summary', 'content'), 280)
        if summary.lower().startswith(title.lower()[:40]):
            summary = summary[len(title):].strip(' -–:|')
        date = parse_date(_text(el, 'pubdate', 'date', 'published', 'updated'))
        link = link.strip()
        items.append({
            'id': hashlib.sha1(link.encode()).hexdigest()[:16],
            'title': title,
            'summary': summary,
            'link': link,
            'source': feed['name'],
            'lang': feed.get('lang', ''),
            'published': date.isoformat() if date else None,
            'img': image(el),
        })
    return items


TG_POST = re.compile(r'data-post="([\w]+/\d+)"')
TG_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
PROMO = re.compile(r'(?:Join our|Follow us|Subscribe to|Read more:|📲|🔗\s*(?:WhatsApp|Telegram|Instagram|Website))', re.I)
TG_TIME = re.compile(r'<time datetime="([^"]+)"')
# channel posts open with alarm emoji and tags ('⚡️', 'Breaking |', 'عاجل |', 'Gaza sources'); a headline needs none
POST_TAGS = re.compile(r'^(?:[←-⯿\U0001f000-\U0001faff️‍\s]'
                       r'|(?:breaking|urgent|watch|video|update|just in|عاجل|متابعة|فيديو)\s*[|:\-–]\s*'
                       r'|(?:gaza|west bank|lebanon|lebanese|syria|syrian|yemen|yemeni|iran|iranian|iraqi|israeli|hebrew|'
                       r'palestinian|local|medical|security) sources\s+(?!say|said|report|told|claim))+',
                       re.I)
URL = re.compile(r'https?://\S+|www\.\S+')
SIGN_OFF = re.compile(r'\[[^\]\n]{1,20}\]')   # '[Ak]': the initials of whoever posted it
# a full stop after these is no sentence end ('Secondary School No. 9', 'Gen. Halevi', 'J. Smith')
ABBREV = re.compile(r'(?:\b(?:No|Nr|Dr|Mr|Mrs|Ms|St|Gen|Lt|Col|Maj|Capt|Sgt|Prof|Sen|Rep|Gov|Jr|Sr|vs|etc|ca|bl\.a|f\.eks)|\b[A-Z])\.$')


def tidy_post(text):
    return POST_TAGS.sub('', text).strip()


def headline(text, limit=160):
    """A post's first sentence as its headline (not cut after 'No.' or an initial), else its first words."""
    for m in re.finditer(r'[.!?](?=\s)', text[:limit]):
        if m.start() > 30 and not ABBREV.search(text[:m.end()]):
            return text[:m.end()], text[m.end():]
    if len(text) <= 140:
        return text, ''
    cut = text[:140].rsplit(' ', 1)[0]
    return cut + ' …', text[len(cut):]


ARABIC = re.compile(r'[؀-ۿ]')
TURKISH = re.compile(r'[ğışİĞŞ]')   # letters English and Danish never use
ENGLISH = re.compile(r"\b(?:the|of|and|to|in|on|for|with|from|after|over|amid|says|said|is|are|was|has|have|by|at)\b", re.I)


def sniff(text, lang):
    """The channel's own language, unless one post is plainly in another: some channels mix English, Turkish
    and Arabic posts, and a Turkish post filed as English would reach the owner untranslated."""
    letters = sum(ch.isalpha() for ch in text)
    if not letters:
        return lang
    arabic = len(ARABIC.findall(text)) / letters
    if lang != 'ar' and arabic > .5:
        return 'ar'
    if lang == 'ar' and arabic < .1 and ENGLISH.search(text):
        return 'en'
    if lang == 'en' and not ENGLISH.search(text) and sum(1 for w in text.split() if TURKISH.search(w)) >= 2:
        return 'tr'
    return lang


def parse_telegram(page, feed):
    """Read the public web preview of a Telegram channel (t.me/s/<channel>)."""
    items = []
    blocks = TG_POST.split(page)
    for post, body in zip(blocks[1::2], blocks[2::2]):
        m = TG_TEXT.search(body)
        if not m:
            continue
        # line by line: links and sign-offs out, 'Join our platforms / Follow us' footers and opening tags off
        lines = [URL.sub('', SIGN_OFF.sub('', clean(l))).strip(' -–|') for l in re.split(r'<br\s*/?>', m.group(1))]
        lines = [l for l in lines if l and not PROMO.match(l)]
        text = tidy_post(PROMO.split(' '.join(lines))[0])
        if len(text) < 20:
            continue
        first = tidy_post(lines[0]) if lines else ''
        if 20 <= len(first) <= 160 and len(lines) > 1 and text.startswith(first):
            title, rest = first, text[len(first):]   # a post with a first line of its own: that line is the headline
        else:
            title, rest = headline(text)
        t = TG_TIME.search(body)
        date = parse_date(t.group(1)) if t else None
        link = f'https://t.me/{post}'
        items.append({
            'id': hashlib.sha1(link.encode()).hexdigest()[:16], 'title': title,
            'summary': clean(rest, 280).strip(' -–:|'), 'link': link,
            'source': feed['name'], 'lang': sniff(text, feed.get('lang', '')), 'published': date.isoformat() if date else None,
        })
    return items


def feed_url(feed):
    kind = feed.get('type', 'rss')
    if kind == 'telegram':
        return f"https://t.me/s/{feed['channel']}"
    if kind == 'youtube':
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={feed['channel']}"
    if kind == 'gnews':
        loc = feed.get('locale', 'en-US:US')
        hl, gl = loc.split(':')
        q = urllib.parse.quote(feed['query'])
        return f'https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={gl}:{hl.split("-")[0]}'
    return feed['url']


def fetch_one(feed, timeout=20):
    req = urllib.request.Request(feed_url(feed), headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/xml, text/xml, text/html, */*'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if data[:2] == b'\x1f\x8b':   # some servers send gzip whether asked or not (Middle East Eye)
            data = gzip.decompress(data)
        if feed.get('type') == 'telegram':
            items = parse_telegram(data.decode('utf-8', 'replace'), feed)
        else:
            items = parse(data, feed)
        if feed.get('type') == 'gnews':
            for it in items:
                it['title'] = it['title'].rsplit(' - ', 1)[0] if ' - ' in it['title'] else it['title']
                it['summary'] = ''
        return feed['name'], items, None
    except Exception as e:  # one broken feed must never stop the radar
        return feed['name'], [], f'{type(e).__name__}: {e}'[:200]


def fetch_all(feeds):
    status, items = {}, []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for name, got, err in pool.map(fetch_one, feeds):
            status[name] = {'ok': err is None, 'items': len(got), 'error': err}
            items.extend(got)
    return items, status
