"""An old article Google News carries again as new (the owner, 18/10: 'undersøg de gamle artikler der kommer igen').

A scout's search of Google News (feeds.json, `scout: true`) found ABC's report of Trump's 'Tuesday 8 p.m.' deadline to
Iran, dated 16 October – the article was April's; Google dates a page anew when its outlet touches it. Of 149 Google
News items in the pool that day only the scouts' two were old (the outlets' own `site:` feeds were not), so the scouts'
new items are checked here before they enter: Google's link is resolved to the outlet's own address, whose path may
carry its month (/2026/04/), and the page's own date is read (datePublished, article:published_time). An item older
than `days` is left out; one whose date cannot be told is kept, as before. Stdlib only.

real_date(link) -> datetime or None; old(items, now, days) -> (the ids found old, the ids not checked this pass)."""
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
PATH_DATE = re.compile(r'/(20\d\d)[/-](0[1-9]|1[0-2])(?:[/-](0[1-9]|[12]\d|3[01]))?/')
PAGE_DATE = [re.compile(p) for p in (
    r'"datePublished"\s*:\s*"([^"]+)"',
    r'property="article:published_time"\s+content="([^"]+)"',
    r'content="([^"]+)"\s+property="article:published_time"',
    r'name="(?:publish-date|pubdate|parsely-pub-date)"\s+content="([^"]+)"')]
TIMEOUT = 8
PER_RUN = 40   # checks a pass: a scout's first search brings many at once, the rest wait for the next pass


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(600_000).decode('utf-8', 'replace')


def resolve(link):
    """The outlet's own address behind a Google News link (its 'batchexecute' call, as news.google.com does), or None."""
    gid = urllib.parse.urlparse(link).path.rstrip('/').split('/')[-1]
    page = get(f'https://news.google.com/rss/articles/{gid}')
    sg, t = re.search(r'data-n-a-sg="([^"]+)"', page), re.search(r'data-n-a-ts="([^"]+)"', page)
    if not (sg and t):
        return None
    inner = json.dumps(['garturlreq', [['X', 'X', ['X', 'X'], None, None, 1, 1, 'US:en', None, 1, None, None, None, None,
                                        None, 0, 1], 'X', 'X', 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                        gid, int(t.group(1)), sg.group(1)])
    body = urllib.parse.urlencode({'f.req': json.dumps([[['Fbv4je', inner, None, 'generic']]])}).encode()
    txt = get('https://news.google.com/_/DotsSplashUi/data/batchexecute', body,
              {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
    url = json.loads(json.loads(txt.split('\n\n')[1])[0][2])[1]
    return url if isinstance(url, str) and url.startswith('http') else None


def when(s):
    try:
        d = datetime.fromisoformat(s.strip().replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def path_date(url):
    """The month (or day) an address carries in its path, as the last moment it can mean."""
    m = PATH_DATE.search(urllib.parse.urlparse(url or '').path)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    if m.group(3):
        return datetime(y, mo, int(m.group(3)), 23, 59, tzinfo=timezone.utc)
    nxt = datetime(y + (mo == 12), mo % 12 + 1, 1, tzinfo=timezone.utc)
    return nxt - timedelta(seconds=1)


def real_date(link):
    """When the article behind a Google News link was published, by its address or its page; None when unknown."""
    try:
        url = resolve(link) if 'news.google.com' in link else link
    except Exception:
        return None
    if not url:
        return None
    by_path = path_date(url)
    try:
        page = get(url)
    except Exception:
        return by_path
    for p in PAGE_DATE:
        m = p.search(page)
        if m and when(m.group(1)):
            return when(m.group(1))
    return by_path


def old(items, now, days=2, look=real_date):
    """(ids of items published more than `days` before now, ids left for the next pass). The address's own month is
    read first (no request); the rest are looked up, at most PER_RUN a pass."""
    cut = now - timedelta(days=days)
    found, todo = set(), []
    for it in items:
        d = path_date(it['link'])
        if d and d < cut:
            found.add(it['id'])
        else:
            todo.append(it)
    later = {it['id'] for it in todo[PER_RUN:]}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for it, d in zip(todo[:PER_RUN], pool.map(lambda it: look(it['link']), todo[:PER_RUN])):
            if d and d < cut:
                found.add(it['id'])
    return found, later
