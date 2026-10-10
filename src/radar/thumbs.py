"""Small square pictures for the cards. Each card takes its own feed image, else another outlet's image of the
same story, else the article page's share image (og:image), shrunk to a 144 px JPEG of a few kilobytes that the
app loads from the data branch (t/<name>.jpg). Telegram channels never lend a picture: their photos are often
raw war footage. Pictures that cannot be fetched, icons and banners are skipped and remembered for a few days."""
import hashlib
import html
import io
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
SIZE = 144
SHARE_META = re.compile(r'<meta\b[^>]*(?:property|name)\s*=\s*["\'](?:og:image(?::secure_url|:url)?|twitter:image(?::src)?)["\'][^>]*>', re.I)
CONTENT = re.compile(r'\bcontent\s*=\s*["\']([^"\']+)["\']', re.I)
NO_PAGE = re.compile(r'^https?://(?:[\w-]+\.)?(?:news\.google\.com|t\.me|youtube\.com|youtu\.be)/', re.I)
# a site's stand-in picture when an article has none of its own (bt.dk/brands/bt/share.jpg is the B.T. logo)
STAND_IN = re.compile(r'/(?:brands?|logos?)/|[/_-](?:logo|share|default|placeholder|fallback)[\w-]*\.(?:jpe?g|png|webp|gif)(?:[?#]|$)', re.I)


def name_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16] + '.jpg'


def share_image(page, base):
    """The picture a page shows when it is shared (og:image / twitter:image), as an absolute URL."""
    for tag in SHARE_META.findall(page):
        m = CONTENT.search(tag)
        url = html.unescape(m.group(1)).strip() if m else ''
        if url and not url.startswith('data:'):
            return urljoin(base, url)
    return ''


def get(url, limit, accept, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit)


def shrink(raw):
    """A centred square JPEG, or None for what is no photo: icons, logos, banners, unreadable files."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        if min(w, h) < 120 or max(w, h) > 2.6 * min(w, h):
            return None
        im.draft('RGB', (SIZE * 2, SIZE * 2))   # JPEGs decode straight at a smaller size
        im = ImageOps.exif_transpose(im).convert('RGB')
        im = ImageOps.fit(im, (SIZE, SIZE), Image.LANCZOS, centering=(.5, .42))
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=72, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001 – a broken picture is no picture
        return None


def attach(cards, members_of, unverified, folder, memory, now=None, page_budget=30, image_budget=50, seconds=40):
    """Give each card a 'thumb' (a file name in `folder`) and delete the files no card uses any more.
    memory: {'page': {article link: [its share image or '', when]}, 'bad': {image url: when}}, kept between runs."""
    import PIL  # noqa: F401 – without Pillow (local test runs) the caller skips pictures altogether
    now = now or datetime.now(timezone.utc)
    since, retry = (now - timedelta(days=3)).isoformat(), (now - timedelta(hours=6)).isoformat()
    # a page that gave no picture (slow, blocked, none) is asked again after 6 hours
    pages = {k: v for k, v in memory.get('page', {}).items() if v[1] >= (since if v[0] else retry)}
    bad = {k: v for k, v in memory.get('bad', {}).items() if v >= since}
    folder.mkdir(parents=True, exist_ok=True)
    have = {p.name for p in folder.glob('*.jpg')}

    def own(it):   # the card and its other outlets, without unverified channels
        return [m for m in [it] + members_of.get(it['id'], []) if m['source'] not in unverified]

    def options(it):
        """Picture URLs for a card, best first; ('page', link) where only the article page can tell."""
        mine = own(it)
        out = [m['img'] for m in mine if m.get('img')]
        if mine and not NO_PAGE.match(mine[0]['link']):
            known = pages.get(mine[0]['link'])
            out.append(known[0] if known else ('page', mine[0]['link']))
        return [o for o in out if o]

    # a site's stand-in (its logo, a default picture) is no photo of the story: it is named so, or two
    # different stories or articles show the very same picture
    shown_by = {}
    for it in cards:
        for o in options(it):
            if isinstance(o, str):
                shown_by.setdefault(o, set()).add(it['id'])
    leads = {mine[0]['link'] for it in cards for mine in [own(it)] if mine}
    for link, (url, _) in pages.items():
        if url and link not in leads:
            shown_by.setdefault(url, set()).add(link)
    for url, who in shown_by.items():
        if len(who) > 1 or STAND_IN.search(url):
            bad[url] = now.isoformat()

    todo = {}
    for it in cards:
        it.pop('thumb', None)
        opts = [o for o in options(it) if o not in bad]
        ready = next((o for o in opts if isinstance(o, str) and name_of(o) in have), None)
        if ready:                        # a picture made in an earlier run stays, so cards do not flicker
            it['thumb'] = name_of(ready)
        elif opts:
            todo[it['id']] = opts[0]

    start = time.monotonic()

    def look(link):
        if time.monotonic() - start > seconds:
            return link, None
        try:
            page = get(link, 300_000, 'text/html,application/xhtml+xml').decode('utf-8', 'replace')
            return link, share_image(page, link)
        except Exception:  # noqa: BLE001 – paywall, block or timeout: no picture from this page
            return link, ''

    links = list(dict.fromkeys(o[1] for o in todo.values() if isinstance(o, tuple)))[:page_budget]
    with ThreadPoolExecutor(8) as pool:
        for link, url in pool.map(look, links):
            if url is not None:
                pages[link] = [url, now.isoformat()]
    for k, o in list(todo.items()):
        if isinstance(o, tuple):
            url = pages.get(o[1], [''])[0]
            if url and url not in bad and not STAND_IN.search(url):
                todo[k] = url
            else:
                del todo[k]
    for url in {u for u in todo.values() if list(todo.values()).count(u) > 1}:   # one stand-in, two new stories
        bad[url] = now.isoformat()
        todo = {k: u for k, u in todo.items() if u != url}

    def fetch(url):
        if time.monotonic() - start > seconds:
            return url, None               # out of time: try again next run
        try:
            return url, shrink(get(url, 8_000_000, 'image/jpeg,image/png,image/webp,image/*;q=.8')) or False
        except Exception:  # noqa: BLE001
            return url, False

    made = {}
    with ThreadPoolExecutor(8) as pool:
        for url, jpg in pool.map(fetch, list(dict.fromkeys(todo.values()))[:image_budget]):
            if jpg:
                (folder / name_of(url)).write_bytes(jpg)
                made[url] = name_of(url)
            elif jpg is False:
                bad[url] = now.isoformat()
    for it in cards:
        if 'thumb' not in it and todo.get(it['id']) in made:
            it['thumb'] = made[todo[it['id']]]

    used = {it['thumb'] for it in cards if it.get('thumb')}
    for p in folder.glob('*.jpg'):
        if p.name not in used:
            p.unlink()
    return {'page': pages, 'bad': bad}
