"""Small square pictures for the cards. Each card takes its own feed image, else another outlet's image of the
same story, else the share image (og:image) of its article page and then of the other outlets' pages, and as a last
resort the picture the editor found for it (summaries.json `images`: the story's own from an article, or an archive
photo of the person or place from Wikimedia Commons, with its credit). Shrunk to a small JPEG of a few kilobytes that
the app loads from the data branch (t/<name>.jpg). Telegram channels never lend a picture: their photos are often
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
SIZE = (330, 300)   # the picture fills the right of a story row and fades out; sharp on a 3x phone screen
SHARE_META = re.compile(r'<meta\b[^>]*(?:property|name)\s*=\s*["\'](?:og:image(?::secure_url|:url)?|twitter:image(?::src)?)["\'][^>]*>', re.I)
CONTENT = re.compile(r'\bcontent\s*=\s*["\']([^"\']+)["\']', re.I)
NO_PAGE = re.compile(r'^https?://(?:[\w-]+\.)?(?:news\.google\.com|t\.me|youtube\.com|youtu\.be)/', re.I)
# a site's stand-in picture when an article has none of its own (bt.dk/brands/bt/share.jpg is the B.T. logo)
STAND_IN = re.compile(r'/(?:brands?|logos?)/|[/_-](?:logo|share|default|placeholder|fallback)[\w-]*\.(?:jpe?g|png|webp|gif)(?:[?#]|$)', re.I)


CUT = 'face1'   # change it when pictures are cut differently: every card then gets a freshly made one


def name_of(url):
    return hashlib.sha1((CUT + url).encode()).hexdigest()[:16] + '.jpg'


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


def focus(im):
    """Where the picture's subject is: the centre of its biggest face as fractions (x, y), or None. Uses OpenCV's
    built-in face finder when it is installed (it is in the cloud); without it every picture is cut as before."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    small = im.copy()
    small.thumbnail((480, 480))
    gray = cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY)
    finder = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    side = max(24, min(gray.shape) // 12)   # tiny faces in a crowd are no subject
    faces = finder.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(side, side))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x + w / 2) / gray.shape[1], (y + h / 2) / gray.shape[0]


def crop_box(size, target, at):
    """The largest box of the target's shape inside `size` that puts the point `at` (fractions) at the box's
    horizontal middle and about a third from its top, as far as the picture's edges allow."""
    (w, h), (tw, th) = size, target
    bw, bh = (w, w * th / tw) if w / h < tw / th else (h * tw / th, h)
    left = min(max(at[0] * w - bw / 2, 0), w - bw)
    top = min(max(at[1] * h - bh * .36, 0), h - bh)
    return round(left), round(top), round(left + bw), round(top + bh)


def shrink(raw):
    """A JPEG cut around the picture's subject (a face when there is one, else a little above the middle, where
    news photos have it), or None for what is no photo: icons, logos, banners, unreadable files."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        if min(w, h) < 120 or max(w, h) > 2.6 * min(w, h):
            return None
        im.draft('RGB', (SIZE[0] * 2, SIZE[1] * 2))   # JPEGs decode straight at a smaller size
        im = ImageOps.exif_transpose(im).convert('RGB')
        im = im.crop(crop_box(im.size, SIZE, focus(im) or (.5, .4))).resize(SIZE, Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=70, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001 – a broken picture is no picture
        return None


def attach(cards, members_of, unverified, folder, memory, now=None, page_budget=30, image_budget=50, seconds=40, chosen=None):
    """Give each card a 'thumb' (a file name in `folder`) and delete the files no card uses any more.
    memory: {'page': {article link: [its share image or '', when]}, 'bad': {image url: when}}, kept between runs.
    chosen: {story id: {'url', 'credit', 'kind'}} – the editor's pictures, tried when nothing else gives one."""
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

    chosen = chosen or {}
    trusted = {c['url'] for c in chosen.values() if c.get('url')}   # the editor's: one portrait may serve two stories

    def editors(it):
        return next((chosen[m['id']] for m in [it] + members_of.get(it['id'], []) if chosen.get(m['id'], {}).get('url')), None)

    def options(it):
        """Picture URLs for a card, best first; ('page', link) where only the article page can tell: the feed
        pictures, then the share pictures of the article pages (the lead's first), then the editor's."""
        mine = own(it)
        out = [m['img'] for m in mine if m.get('img')]
        for m in mine[:5]:
            if not NO_PAGE.match(m['link']):
                known = pages.get(m['link'])
                out.append(known[0] if known else ('page', m['link']))
        pick = editors(it)
        if pick:
            out.append(pick['url'])
        return [o for o in out if o]

    # a site's stand-in (its logo, a default picture) is no photo of the story: it is named so, or two
    # different stories or articles show the very same picture
    shown_by = {}
    for it in cards:
        for o in options(it):
            if isinstance(o, str):
                shown_by.setdefault(o, set()).add(it['id'])
    page_of = {m['link']: it['id'] for it in cards for m in own(it)}   # an article page counts for its own card
    for link, (url, _) in pages.items():
        if url:
            shown_by.setdefault(url, set()).add(page_of.get(link, link))
    for url, who in shown_by.items():
        if url not in trusted and (len(who) > 1 or STAND_IN.search(url)):
            bad[url] = now.isoformat()

    todo = {}
    for it in cards:
        it.pop('thumb', None)
        it.pop('pic', None)
        opts = [o for o in options(it) if o not in bad]
        ready = next((o for o in opts if isinstance(o, str) and name_of(o) in have), None)
        if ready:                        # a picture made in an earlier run stays, so cards do not flicker
            it['thumb'], it['pic'] = name_of(ready), ready   # pic: the original, for the big lead picture
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
    for url in {u for u in todo.values() if list(todo.values()).count(u) > 1} - trusted:   # one stand-in, two stories
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
            it['thumb'], it['pic'] = made[todo[it['id']]], todo[it['id']]
        it.pop('pic_credit', None)
        pick = editors(it)
        if pick and it.get('pic') == pick['url'] and pick.get('kind') == 'archive':
            it['pic_credit'] = pick.get('credit') or 'Arkivfoto'   # an archive photo says so, with its photographer

    used = {it['thumb'] for it in cards if it.get('thumb')}
    for p in folder.glob('*.jpg'):
        if p.name not in used:
            p.unlink()
    return {'page': pages, 'bad': bad}
