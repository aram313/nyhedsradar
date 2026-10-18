"""Small square pictures for the cards. Each card takes its own feed image, else another outlet's image of the
same story, else the share image (og:image) of its article page and then of up to four other outlets' pages, shrunk
to a small JPEG of a few kilobytes that the app loads from the data branch (t/<name>.jpg); a story with none shows its
outlet's initials in the app. Telegram channels never lend a picture: their photos are often
raw war footage. Pictures that cannot be fetched, icons and banners are skipped and remembered for a few days."""
import hashlib
import html
import io
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
SIZE = (330, 300)   # the picture fills the right of a story row and fades out; sharp on a 3x phone screen
SHARE_META = re.compile(r'<meta\b[^>]*(?:property|name)\s*=\s*["\'](?:og:image(?::secure_url|:url)?|twitter:image(?::src)?)["\'][^>]*>', re.I)
CONTENT = re.compile(r'\bcontent\s*=\s*["\']([^"\']+)["\']', re.I)
NO_PAGE = re.compile(r'^https?://(?:[\w-]+\.)?(?:news\.google\.com|t\.me|youtube\.com|youtu\.be)/', re.I)
# a site's stand-in picture when an article has none of its own (bt.dk/brands/bt/share.jpg is the B.T. logo)
STAND_IN = re.compile(r'/(?:brands?|logos?)/|[/_-](?:logo|share|default|placeholder|fallback)[\w-]*\.(?:jpe?g|png|webp|gif)(?:[?#]|$)', re.I)


SPOT_AGAIN = 8   # pictures made before the subject was kept, looked at again in a run (18/10)
# The large pictures (18/10, the owner: 'Er det ikke bedre at finde billeder der passer bedre til dagens historie frem
# for at fjerne teksten fra billedet?' – and 'Billederne tager alt for lang tid at loade. Næsten et sekund ved opstart':
# the outlets' originals weigh up to a few MB): for the stories the app may show large, every outlet's picture of the
# story is graded for a headline on its lower part, and the best is kept as a light copy (state/l/, LARGE_W wide)
LARGE_W = 960        # px: sharp across a phone's width at 2-3x, about a twentieth of an outlet's original
LARGE_CARDS = 18     # the strongest stories in Live (and the big ones) whose pictures are graded
LARGE_BUDGET = 14    # originals graded in a run (the rest the next runs)
LARGE_PAGES = 16     # article pages looked at in a run for their share pictures
LARGE_SECONDS = 20
LARGE_EACH = 5       # an outlet's pictures graded for a story: the lead's and four others'
# the owner chooses among a story's best pictures (18/10, the owner: 'kan jeg som admin få lov til at vælge mellem 3
# billeder når jeg holder nede på de store artikler på forsiden … redaktøren vil også i fremtiden lære af dette og forstå
# min smag for billedvalg'): the best CHOICES with their light copies on the card ('pics'); his choice wins for the story,
# and each one teaches the grading his taste (`taste`: a weight per feature and per outlet, learned from the chosen
# against the others it beat – a bonus of at most TASTE_MAX on a picture's fitness)
CHOICES = 3
TASTE_MAX, TASTE_RATE = 2.0, 0.5
FEATURES = ('face', 'small_face', 'close', 'wide', 'upright', 'sharp')
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
    """Where the picture's subject is: the centre of its biggest face as fractions (x, y), or None."""
    box = face_box(im)
    return box[:2] if box else None


def face_box(im):
    """The picture's biggest face: (x, y, height) as fractions of the picture – its centre and its height – or None.
    Uses OpenCV's built-in face finder when it is installed (it is in the cloud); without it every picture is cut as
    before."""
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
    return (x + w / 2) / gray.shape[1], (y + h / 2) / gray.shape[0], h / gray.shape[0]


def subject(raw):
    """Where a picture's subject sits and its shape, for the app's large pictures with text on them (the owner, 18/10:
    'Teksten dækker for rubios ansigt, der skal vurderes om det er et godt nok billede til forside i sådanne tilfælde'):
    [x, y, width/height, 1 for a face or 0, the face's height] – the centre of its biggest face as fractions, else the
    middle a little above its centre; None for no picture. The face's height (18/10: the text still covered Rubio's
    mouth – the app knew only where the face's centre sat) lets the app keep the whole face clear of the text."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        im.draft('RGB', (960, 960))
        im = ImageOps.exif_transpose(im).convert('RGB')
        w, h = im.size
        at = face_box(im)
        x, y, fh = at or (.5, .4, 0)
        return [round(x, 3), round(y, 3), round(w / h, 3), 1 if at else 0, round(fh, 3)]
    except Exception:  # noqa: BLE001 – a broken picture is no picture
        return None


def crop_box(size, target, at):
    """The largest box of the target's shape inside `size` that puts the point `at` (fractions) at the box's
    horizontal middle and about a third from its top, as far as the picture's edges allow."""
    (w, h), (tw, th) = size, target
    bw, bh = (w, w * th / tw) if w / h < tw / th else (h * tw / th, h)
    left = min(max(at[0] * w - bw / 2, 0), w - bw)
    top = min(max(at[1] * h - bh * .36, 0), h - bh)
    return round(left), round(top), round(left + bw), round(top + bh)


# a night shot in which almost nothing can be seen is no picture for a story (the front page's review, 18/10: Dagens
# historie wore DR's photo of Rubio at night – its mean light 18 of 255, its brightest tenth under 43; among 60 cards'
# pictures the next darkest had 35 and 117): another outlet's picture of the story is taken instead
DARK_MEAN, DARK_P90 = 28, 80


def too_dark(im):
    """Whether a picture is too dark to show: its mean light under DARK_MEAN and its brightest tenth under DARK_P90."""
    g = im.convert('L').resize((66, 60))
    h = g.histogram()
    n = sum(h) or 1
    mean = sum(i * c for i, c in enumerate(h)) / n
    acc, p90 = 0, 255
    for i, c in enumerate(h):
        acc += c
        if acc >= .9 * n:
            p90 = i
            break
    return mean < DARK_MEAN and p90 < DARK_P90


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
        if too_dark(im):
            return None
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=70, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001 – a broken picture is no picture
        return None


def fitness(w, h, mean, pf):
    """How well a picture carries a headline on its lower part, as the app sets it: wide, sharp, light enough, and its
    subject a scene or a face small and high – a close portrait leaves no room for the text (pf: subject's [x, y, ar,
    face, face height])."""
    ar, s = w / h, 0.0
    s += 2 if 1.3 <= ar <= 2.1 else 0 if ar >= 1.0 else -3
    s += 1 if min(w, h) >= 700 else -2 if w < 600 else 0
    s -= 1.5 if mean < 45 else 0
    face, fy, fh = pf[3], pf[1], pf[4] if len(pf) > 4 else 0
    if not face:
        s += 1
    elif fh <= 0.22:
        s += 1 + (0.5 if fy <= 0.5 else 0)
    elif fh <= 0.35:
        s -= 1
    else:
        s -= 3
    return round(s, 2)


def pic_key(url):
    """A picture's short name, as the app and the owner's choice give it."""
    return name_of(url)[:16]


def features(url, g):
    """What the owner's taste is learned on: a picture's face and its size, its shape, its size in pixels; its outlet."""
    pf = (g or [0, [0, 0, 1.5, 0, 0]])[1]
    ar, face, fh = pf[2], pf[3], pf[4] if len(pf) > 4 else 0
    f = {'face': 1.0 if face else 0.0, 'small_face': 1.0 if face and fh <= 0.22 else 0.0, 'close': 1.0 if face and fh > 0.35 else 0.0,
         'wide': 1.0 if 1.3 <= ar <= 2.1 else 0.0, 'upright': 1.0 if ar < 1.0 else 0.0, 'sharp': 1.0 if g and g[0] >= 2 else 0.0}
    return f, urlsplit(url).hostname or ''


def taste_bonus(taste, url, g):
    """The owner's learned taste for a picture: a bonus (or a penalty) of at most TASTE_MAX."""
    if not taste:
        return 0.0
    f, host = features(url, g)
    w = taste.get('w') or {}
    b = sum(w.get(k, 0.0) * v for k, v in f.items()) + max(-1.0, min(1.0, 0.3 * (taste.get('hosts') or {}).get(host, 0.0)))
    return max(-TASTE_MAX, min(TASTE_MAX, b))


def learn(taste, chosen, others, graded):
    """One choice of the owner's: the chosen picture's features weigh up, the ones it was chosen over weigh down."""
    taste = {'w': dict(taste.get('w') or {}), 'hosts': dict(taste.get('hosts') or {}), 'n': int(taste.get('n') or 0),
             'seen': list(taste.get('seen') or [])}
    fc, hc = features(chosen, graded.get(chosen))
    for u in others:
        fo, ho = features(u, graded.get(u))
        for k in FEATURES:
            taste['w'][k] = round(taste['w'].get(k, 0.0) + TASTE_RATE * (fc[k] - fo[k]) / max(1, len(others)), 3)
        if ho and ho != hc:
            taste['hosts'][ho] = round(taste['hosts'].get(ho, 0.0) - 0.5 / max(1, len(others)), 3)
    if hc:
        taste['hosts'][hc] = round(taste['hosts'].get(hc, 0.0) + 1.0, 3)
    taste['n'] += 1
    return taste


def grade(raw):
    """A picture for a large frame: (its fitness, where its subject sits, a light JPEG copy LARGE_W wide), or None for
    one that is too small, too narrow, too dark or unreadable."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        if min(w, h) < 300 or max(w, h) > 2.6 * min(w, h):
            return None
        im.draft('RGB', (LARGE_W * 2, LARGE_W * 2))
        im = ImageOps.exif_transpose(im).convert('RGB')
        if too_dark(im):
            return None
        g = im.convert('L').resize((64, 64))
        mean = sum(g.getdata()) / 4096
        box = face_box(im)
        x, y, fh = box or (.5, .4, 0)
        pf = [round(x, 3), round(y, 3), round(w / h, 3), 1 if box else 0, round(fh, 3)]
        if im.width > LARGE_W:
            im = im.resize((LARGE_W, round(im.height * LARGE_W / im.width)), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=68, optimize=True, progressive=True)
        return fitness(w, h, mean, pf), pf, out.getvalue()
    except Exception:  # noqa: BLE001 – a broken picture is no picture
        return None


def attach(cards, members_of, unverified, folder, memory, now=None, page_budget=30, image_budget=50, seconds=40, chosen_by=None):
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
    # a picture made before the darkness rule is looked at once (18/10): a too dark one is set aside as no picture
    lit = dict(memory.get('lit', {}))
    # where the subject of each large picture sits (subject): kept per picture, the ones made before looked at a few a run
    spot = dict(memory.get('spot', {}))

    def bright(url):
        name = name_of(url)
        if name not in lit:
            from PIL import Image
            try:
                with Image.open(folder / name) as im:
                    lit[name] = not too_dark(im)
            except Exception:  # noqa: BLE001 – an unreadable file is made again
                lit[name] = False
            if not lit[name]:
                bad[url] = now.isoformat()
        return lit[name]

    def own(it):   # the card and its other outlets, without unverified channels
        return [m for m in [it] + members_of.get(it['id'], []) if m['source'] not in unverified]

    def options(it):
        """Picture URLs for a card, best first; ('page', link) where only the article page can tell: the feed
        pictures, then the share pictures of the article pages (the lead's first)."""
        mine = own(it)
        out = [m['img'] for m in mine if m.get('img')]
        for m in mine[:5]:
            if not NO_PAGE.match(m['link']):
                known = pages.get(m['link'])
                out.append(known[0] if known else ('page', m['link']))
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
        if len(who) > 1 or STAND_IN.search(url):
            bad[url] = now.isoformat()

    todo = {}
    for it in cards:
        it.pop('thumb', None)
        it.pop('pic', None)
        opts = [o for o in options(it) if o not in bad]
        ready = next((o for o in opts if isinstance(o, str) and name_of(o) in have and bright(o)), None)
        opts = [o for o in opts if o not in bad]
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
    for url in {u for u in todo.values() if list(todo.values()).count(u) > 1}:   # one stand-in, two new stories
        bad[url] = now.isoformat()
        todo = {k: u for k, u in todo.items() if u != url}

    def fetch(url):
        if time.monotonic() - start > seconds:
            return url, None, None         # out of time: try again next run
        try:
            raw = get(url, 8_000_000, 'image/jpeg,image/png,image/webp,image/*;q=.8')
            jpg = shrink(raw)
            return url, jpg or False, subject(raw) if jpg else None
        except Exception:  # noqa: BLE001
            return url, False, None

    made = {}
    with ThreadPoolExecutor(8) as pool:
        for url, jpg, where in pool.map(fetch, list(dict.fromkeys(todo.values()))[:image_budget]):
            if jpg:
                (folder / name_of(url)).write_bytes(jpg)
                made[url] = name_of(url)
                if where:
                    spot[url] = where
            elif jpg is False:
                bad[url] = now.isoformat()
    for it in cards:
        if 'thumb' not in it and todo.get(it['id']) in made:
            it['thumb'], it['pic'] = made[todo[it['id']]], todo[it['id']]

    # the pictures made before (no spot yet): the original looked at again, a few a run, the strongest cards first
    def look_again(url):
        if time.monotonic() - start > seconds:
            return url, None
        try:
            return url, subject(get(url, 8_000_000, 'image/jpeg,image/png,image/webp,image/*;q=.8'))
        except Exception:  # noqa: BLE001
            return url, None
    again = list(dict.fromkeys(it['pic'] for it in cards if it.get('pic') and len(spot.get(it['pic']) or []) < 5))[:SPOT_AGAIN]
    with ThreadPoolExecutor(4) as pool:
        for url, where in pool.map(look_again, again):
            if where:
                spot[url] = where
    for it in cards:
        if it.get('pic') in spot:
            it['pf'] = spot[it['pic']]

    taste = dict(memory.get('taste') or {})   # the owner's picture taste, learned from his choices
    graded = large(cards, options, pages, bad, dict(memory.get('grade', {})), folder.parent / 'l', now, chosen_by=chosen_by, taste=taste)

    used = {it['thumb'] for it in cards if it.get('thumb')}
    for p in folder.glob('*.jpg'):
        if p.name not in used:
            p.unlink()
    shown = {it.get('pic') for it in cards}
    return {'page': pages, 'bad': bad, 'lit': {k: v for k, v in lit.items() if k in used},
            'spot': {k: v for k, v in spot.items() if k in shown}, 'grade': graded, 'taste': taste}


def large(cards, options, pages, bad, graded, light, now, look=None, chosen_by=None, taste=None):
    """For the strongest stories: their outlets' pictures graded (fitness and the owner's learned taste, at most
    LARGE_EACH a story, the budget shared out story by story), the best kept as the story's large picture (card 'pic' its
    original, 'pf' its subject, 'pl' its light copy in `light`) – or the one the owner chose (chosen_by: {story or member
    id: picture key}) – and its best CHOICES with their copies on the card ('pics', for the owner's choice). graded:
    {url: [fitness, pf] or 0}, kept between runs; taste: what his choices taught (learn), updated in place.
    Returns graded, pruned to the pictures still in question."""
    start = time.monotonic()
    wide = [it for it in sorted(cards, key=lambda c: -(c.get('rank') or 0)) if it.get('live') or it.get('big')][:LARGE_CARDS]
    if not wide:   # no story in question: no copy kept
        for f in light.glob('*.jpg') if light.exists() else []:
            f.unlink()
        return {}
    light.mkdir(parents=True, exist_ok=True)
    cand = {it['id']: options(it) for it in wide}

    def page_of(link):   # its own clock: the small pictures' pass may have used its time
        if time.monotonic() - start > LARGE_SECONDS / 2:
            return link, None
        try:
            return link, share_image(get(link, 300_000, 'text/html,application/xhtml+xml').decode('utf-8', 'replace'), link)
        except Exception:  # noqa: BLE001 – paywall, block or timeout: no picture from this page
            return link, ''
    links = list(dict.fromkeys(o[1] for us in cand.values() for o in us[:LARGE_EACH] if isinstance(o, tuple) and o[1] not in pages))
    with ThreadPoolExecutor(8) as pool:
        for link, url in pool.map(page_of, links[:LARGE_PAGES]):
            if url is not None:
                pages[link] = [url, now.isoformat()]

    def usable(u):
        return isinstance(u, str) and u.startswith('http') and u not in bad and not STAND_IN.search(u)
    for k, us in cand.items():
        flat = [pages.get(u[1], [''])[0] if isinstance(u, tuple) else u for u in us]
        cand[k] = [u for u in dict.fromkeys(flat) if usable(u)][:LARGE_EACH]

    made = {}   # the light copies made in this run, by picture

    def grade_one(url):
        if time.monotonic() - start > LARGE_SECONDS:
            return url, None
        try:
            return url, grade(get(url, 8_000_000, 'image/jpeg,image/png,image/webp,image/*;q=.8')) or 0
        except Exception:  # noqa: BLE001 – no picture from this address
            return url, 0

    def run(urls):
        with ThreadPoolExecutor(6) as pool:
            for url, g in pool.map(grade_one, urls):
                if g is None:
                    continue              # out of time: the next run
                graded[url] = [g[0], g[1]] if g else 0
                if g:
                    made[url] = g[2]
    # story by story: every story's first picture, then every story's second …
    order = [us[k] for k in range(LARGE_EACH) for us in cand.values() if k < len(us) and us[k] not in graded]
    run(list(dict.fromkeys(order))[:LARGE_BUDGET])
    chosen, ranked = {}, {}
    taste = taste if taste is not None else {}
    for it in wide:
        scored = []
        for n, u in enumerate(cand.get(it['id']) or []):
            g = graded.get(u)
            if g:   # the lead's own picture, by a little, when they are alike; the owner's taste on top
                scored.append((g[0] + (0.5 if n == 0 else 0) + taste_bonus(taste, u, g), u))
        scored.sort(key=lambda x: -x[0])
        ranked[it['id']] = [u for _, u in scored[:CHOICES]]
        own = next((chosen_by[k] for k in [it['id'], *(it.get('members') or [])] if (chosen_by or {}).get(k)), None)
        pick = next((u for _, u in scored if pic_key(u) == own), None) if own else None
        if pick:
            chosen[it['id']] = pick
            if pick not in ranked[it['id']]:
                ranked[it['id']] = [pick, *ranked[it['id']][:CHOICES - 1]]
            seen = f"{it['id']}|{own}"
            if seen not in (taste.get('seen') or []):   # each choice teaches once
                taste.update(learn(taste, pick, [u for _, u in scored if u != pick][:CHOICES], graded))
                taste['seen'] = [*(taste.get('seen') or []), seen][-200:]
        elif scored:
            chosen[it['id']] = scored[0][1]
    lname = lambda u: 'l' + name_of(u)   # noqa: E731
    wanted = list(dict.fromkeys([*chosen.values(), *[u for us in ranked.values() for u in us]]))
    # a picture in question whose copy is gone (graded in an earlier run): made again, a few a run
    run([u for u in wanted if u not in made and not (light / lname(u)).exists()][:8])
    for u in wanted:
        if u in made and not (light / lname(u)).exists():
            (light / lname(u)).write_bytes(made[u])
    for it in wide:
        u = chosen.get(it['id'])
        if u and (light / lname(u)).exists() and graded.get(u):
            it['pic'], it['pf'], it['pl'] = u, graded[u][1], lname(u)
        opts = [{'k': pic_key(x), 'u': x, 'pf': graded[x][1], 'pl': lname(x)} for x in ranked.get(it['id']) or []
                if graded.get(x) and (light / lname(x)).exists()]
        if len(opts) >= 2:
            it['pics'] = opts
        else:
            it.pop('pics', None)
    keep = {it['pl'] for it in cards if it.get('pl')} | {o['pl'] for it in cards for o in it.get('pics') or []}
    for f in light.glob('*.jpg'):
        if f.name not in keep:
            f.unlink()
    asked = {u for us in cand.values() for u in us}
    return {u: (g[:2] if g else 0) for u, g in graded.items() if u in asked}
