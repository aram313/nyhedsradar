"""Fetch and parse news feeds (RSS 2.0, RSS 1.0/RDF and Atom) with the standard library only."""
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


def clean(s, limit=None):
    s = html.unescape(TAG.sub(' ', html.unescape(s or '')))
    s = SPACE.sub(' ', s).strip()
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
        })
    return items


TG_POST = re.compile(r'data-post="([\w]+/\d+)"')
TG_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
PROMO = re.compile(r'(?:Join our|Follow us|Subscribe to|Read more:|📲|🔗\s*(?:WhatsApp|Telegram|Instagram|Website))', re.I)
TG_TIME = re.compile(r'<time datetime="([^"]+)"')
# channel posts open with alarm emoji and tags ('⚡️', 'Breaking |', 'عاجل |', 'Gaza sources'); a headline needs none
POST_TAGS = re.compile(r'^(?:[←-⯿\U0001f000-\U0001faff️‍\s]'
                       r'|(?:breaking|urgent|watch|video|update|just in|عاجل|متابعة|فيديو)\s*[|:\-–]\s*'
                       r'|(?:gaza|west bank|lebanon|syria|yemen|iran|israeli|hebrew|palestinian) sources\s+(?!say|said|report|told|claim))+',
                       re.I)


def tidy_post(text):
    return POST_TAGS.sub('', text).strip()


def parse_telegram(page, feed):
    """Read the public web preview of a Telegram channel (t.me/s/<channel>)."""
    items = []
    blocks = TG_POST.split(page)
    for post, body in zip(blocks[1::2], blocks[2::2]):
        m = TG_TEXT.search(body)
        if not m:
            continue
        text = clean(re.sub(r'<br\s*/?>', ' ', m.group(1)))
        text = tidy_post(PROMO.split(text)[0])  # drop 'Join our platforms / Follow us' footers and opening tags
        if len(text) < 20:
            continue
        cut = re.search(r'(?<=[.!?])\s', text[:160])
        if cut and cut.start() > 30:
            title = rest = text[:cut.start()]
        else:
            rest = text[:140].rsplit(' ', 1)[0] if len(text) > 140 else text
            title = rest + (' …' if len(text) > len(rest) else '')
        t = TG_TIME.search(body)
        date = parse_date(t.group(1)) if t else None
        link = f'https://t.me/{post}'
        items.append({
            'id': hashlib.sha1(link.encode()).hexdigest()[:16], 'title': title,
            'summary': clean(text[len(rest):], 280).strip(' -–:|'), 'link': link,
            'source': feed['name'], 'lang': feed.get('lang', ''), 'published': date.isoformat() if date else None,
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
