"""Hizb ut-Tahrir's new political answers – the amir's answers to political questions – followed as a layer of their
own: never a story card and never ranked with the news. The app already holds the answers up to its last build
(public/viden/movement.json, Danish readings only, attributed); a newer answer is found here, and its text is kept in
the radar's state for the editor, who files it in answers.json on the digest branch with Danish readings – the app
shows only the answer as his, attributed ("Ifølge Hizb ut-Tahrirs svar af …"), never an analysis of its own.

The site (hizb-ut-tahrir.info) has no feed and refuses query strings, so the plain list page is read at most every
few hours and the text of a few new answers is fetched per run. The text of an answer the app already holds
('known') is never fetched or kept: the repository is public, and the state branch is part of it."""
import html
import re
import urllib.request
from datetime import datetime, timedelta, timezone

LIST = 'https://www.hizb-ut-tahrir.info/en/index.php/qestions/political-questions.html'
BASE = 'https://www.hizb-ut-tahrir.info'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
KEEP = 40                   # answers remembered (the text only of those the app does not hold yet)
EVERY = timedelta(hours=3)  # how often the list page is read
PER_RUN = 3                 # new answers fetched per run (the rest follow in the next runs)
TEXT_LEN = 40000            # characters of an answer kept (the longest run to about 25,000)

ITEM = re.compile(r'<h4>\s*<a href="(/en/index\.php/qestions/political-questions/(\d+)\.html)">\s*(.*?)\s*</a>\s*</h4>'
                  r'.*?<time datetime="([^"]+)"', re.S)
BODY_END = re.compile(r'<div class="(?:itemLinks|itemSocialSharing|itemAuthorBlock|itemNavigation|itemRelated'
                      r'|itemTagsBlock|itemAttachmentsBlock|itemBackToTop)')


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode('utf-8', 'replace')


def text_of(fragment):
    """Readable text from an HTML fragment: paragraphs kept, tags dropped, entities decoded."""
    t = re.sub(r'<(?:br|/p|/h\d|/li|/div|/blockquote)[^>]*>', '\n', fragment)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n\n', t).strip()


def parse_list(page):
    """The answers on the list page, newest first: id, title, url and the date the site gives (ISO)."""
    out, seen = [], set()
    for path, num, title, when in ITEM.findall(page):
        if num in seen:
            continue
        seen.add(num)
        out.append({'id': num, 'title': text_of(title), 'url': BASE + path, 'date': when})
    return out


def parse_answer(page):
    """The text of one answer (the article body), or '' when the page has none."""
    i = page.find('itemFullText')
    if i < 0:
        return ''
    body = page[page.find('>', i) + 1:]
    end = BODY_END.search(body)
    return text_of(body[:end.start()] if end else body[:200_000])[:TEXT_LEN]


def update(memory, now=None, fetch=get, known=()):
    """memory: {'checked': ISO, 'items': [{id, title, url, date, text, fetched, known}]} kept between runs. Reads
    the list at most every EVERY, fetches the text of up to PER_RUN new answers that have none yet (never of a
    known one: the app holds those already), keeps the newest KEEP. A failing site leaves the memory as it was."""
    now = now or datetime.now(timezone.utc)
    known = set(known)
    memory = {'checked': memory.get('checked', ''), 'items': [dict(x) for x in memory.get('items') or []]}
    have = {x['id']: x for x in memory['items']}
    last = memory['checked']
    if not last or now - datetime.fromisoformat(last) >= EVERY:
        try:
            listed = parse_list(fetch(LIST))
        except Exception:  # noqa: BLE001 – the site is often slow or down; try again next time
            listed = []
        if listed:
            memory['checked'] = now.isoformat(timespec='seconds')
            for x in listed:
                if x['id'] not in have:
                    have[x['id']] = {**x, 'text': '', 'fetched': ''}
    for x in have.values():
        x['known'] = x['id'] in known
        if x['known']:
            x['text'] = ''
    todo = [x for x in sorted(have.values(), key=lambda x: x['date'], reverse=True)
            if not x.get('text') and not x['known']][:PER_RUN]
    for x in todo:
        try:
            text = parse_answer(fetch(x['url']))
        except Exception:  # noqa: BLE001
            continue
        if text:
            x['text'], x['fetched'] = text, now.isoformat(timespec='seconds')
    memory['items'] = sorted(have.values(), key=lambda x: x['date'], reverse=True)[:KEEP]
    return memory


def to_tell(memory, told, now, hours=48):
    """The new answers (the app does not hold them, their text is in) not told about yet, newest first, found in the
    last two days."""
    out = []
    for x in (memory or {}).get('items') or []:
        if x.get('known') or not x.get('text') or x['id'] in told or not x.get('fetched'):
            continue
        try:
            fetched = datetime.fromisoformat(x['fetched'])
        except ValueError:
            continue
        if (now - fetched).total_seconds() <= hours * 3600:
            out.append(x)
    return out


NO_TITLE = 'Et nyt svar på politiske spørgsmål'


def push_title(title):
    """An answer's original title as a notification says it: without 'Answer to Question:', with Khabar's word for Israel."""
    t = re.sub(r'^\s*(?:updated\s+)?(?:ameer\'?s\s+)?(?:answer to (?:a )?questions?|questions? and answers?|q\s*&\s*a)\s*[:\-–]?\s*', '',
               title or '', flags=re.I)
    t = re.sub(r'\b(?:the\s+)?(?:Jewish|Zionist)\s+(?:Entity|State)\b', 'Israel', t, flags=re.I)
    return (t[:1].upper() + t[1:]) if t else NO_TITLE


def for_app(memory):
    """What data.json lists: id, title, date and link of each new answer whose text the radar has (the text and the
    known answers stay out; the app shows the answers it holds from the wiki and the editor's answers.json)."""
    return [{'id': x['id'], 'title': x['title'], 'date': x['date'], 'url': x['url']}
            for x in (memory or {}).get('items') or [] if x.get('text') and not x.get('known')]
