"""Tools for the Claude editor. Khabar is looked at every quarter of an hour: `gate` – plain Python, no tokens – runs
after every radar pass in GitHub Actions, and when something of weight has happened since the last update it fires the
editor's Claude routine through its API trigger, at most EDITOR_FIRES (config/settings.json) times a Danish day
(docs/hjerne/cadence.md). An update is small: only what is new since the last one.

    python3 scripts/editor.py gate [--fire]      -> the look of `check` and, when its verdict holds and no update is
                                                    under way, one fire of the routine (with --fire and the
                                                    ROUTINE_FIRE_URL / ROUTINE_FIRE_TOKEN secrets); the fires of the day
                                                    are kept in the data branch's editor-gate.json
    python3 scripts/editor.py check              -> at most about 40 lines: the radar's health, the last full update,
                                                    what is new since (the stories of weight with their tier and
                                                    outlets, marked when already a pick or in the recap, the wire lines,
                                                    a new answer of Hizb ut-Tahrir), Live (the day's level, how many
                                                    stories are in, how many wait for the editor's headline), the front
                                                    page now and a verdict, INTET NYT AF VÆGT or OPDATÉR: why. The
                                                    routine stops there or updates.
    python3 scripts/editor.py input              -> /tmp/editor/input.md: the brain (scripts/brain.py), the front page
                                                    now, the recap so far, the top stories, the new stories and wire
                                                    lines since the last update, the stories to summarise, the stories
                                                    in Live without the editor's headline, the day's level with the
                                                    candidates at the radar's line, the front page's composition with
                                                    its palette, a new answer to note, and the format
    python3 scripts/editor.py publish FILE       -> checks the update, fills in links, sources and times, and writes
            [--push] [--out DIR]                    digest.json (the day shown, with the editor's picks, moves and
                                                    quotes), moves.json (the last 30 days), summaries.json (the story
                                                    summaries and the editor's headlines of the last 4 days),
                                                    answers.json (Hizb ut-Tahrir's answers noted after the static
                                                    layer, kept forever), live.json (the day's level, take and drop,
                                                    two Danish days), front.json (the front page's blocks) and
                                                    kalender.json (the editor's planned events from the news, kept
                                                    until two days after their day); --push commits them to the
                                                    digest branch, keeping its other files

Each update weighs the news by the brain – the books' order of weight and Hizb ut-Tahrir's newest answers, used only to
choose and order: the lede, the picks, the front page, how much Live holds, Dagens historie and the order of the
recap's topics. The app shows no analysis; the editor's own text (lede, recap lines, summaries, headlines, block
titles, a front page's line) stays reality. An update writes the lede, picks, quotes, short summaries of the stories
readers open, an informative headline for every story Live shows (who did or said what, where – never a curiosity
headline; the owner's rule of 2026-10-17), the day's level (få, normal, mange) with single stories taken in or out,
the front page as blocks of its palette (top, liste, udvikling, citat, svar, live, linje), and 'Who: what' lines for
the day's recap in the style of Al Jazeera's wire and the group's own 'Politiske nyheder' posts, grouped by topic; a
line goes into the day it happened (Danish date), so after midnight what came before completes yesterday's recap. It
may keep the lede, the picks, the quotes, the level and the front page (leave them out, or write "keep"), add only
recap lines, or give only a new lede. Moves (a story in a clearly wrong section) are rare and stay until undone. Only
the first update at or after 21 Danish time notifies the phones.

Reads data.json, app.json, admitted.json, lines.json, items.json and analyses.json from origin/data (or --data-dir, the
radar's state folder in Actions) and digest.json, moves.json, summaries.json, answers.json, live.json and front.json
from origin/digest, or all of them from --dir. Options for test runs: --now ISO."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain  # noqa: E402 – the books' order of weight and Hizb ut-Tahrir's newest answers, for weighing
import voice  # noqa: E402 – Khabar's content rules
import events as event_pages  # noqa: E402 – Begivenheder: the event pages and their fact boxes
import okonomi as econ  # noqa: E402 – the economy editor's day on the Økonomi page
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radar import level as radar_level  # noqa: E402 – how the radar reads live.json (stdlib only)
from radar import headlines as radar_heads  # noqa: E402 – the radar's curiosity test and teaser cleaning (stdlib only)
from radar import energy as radar_energy  # noqa: E402 – the economy page's news patterns (stdlib only)

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {'dk': 'Danmark', 'me': 'Mellemøsten', 'world': 'Verden'}
DAYS = ['mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag']
MONTHS = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober',
          'november', 'december']
KEEP = 30        # days in the archive
MAX_NEW = 5      # lines one update may add: the most important movements since the last
MAX_TEXT = 220   # characters in a line: one short sentence
MAX_SUM = 6      # stories one update summarises: the ones readers open, then the ones they are most likely to
SUM_LEN = 420    # characters in a summary: two or three sentences
SUM_DAYS = 4     # how long a summary (and a checked headline) is kept
MAX_TITLES = 30  # headlines one update writes: every admitted story the app shows without the editor's own, the
                 # strongest first (the owner 2026-10-17: informative headlines, never the outlets' curiosity ones)
TITLE_LEN = 140  # characters in a headline
HEAD_WAIT = 8    # admitted stories waiting for the editor's headline that call for an update
HEAD_LATE = timedelta(minutes=45)   # ... or one that has waited this long (06-24)
TEASER = 200     # characters of an outlet's teaser in the input's headline list
OTHERS = 3       # other outlets' headlines shown with each story to head
LEVELS = ('få', 'normal', 'mange')   # how far down the ranking Live reaches today (docs/hjerne/notes-owner-volume.md)
LEVEL_SIZE = {'få': 25, 'normal': 45, 'mange': 80}   # the owner's first guess of stories in 24 hours, for the input
LIVE_NOTE = 160  # characters of the level's note
LINE_SHOWN = 6   # candidates shown just above and just below the radar's line
# the front page's palette; since 18/10 the event modules (the owner: 'Lav moduler som vores redaktør kan udnytte til den
# fulde potentiale'): 'begivenhed' (an event page's card with its key numbers), 'tal' (one fact, large) and 'nedtaelling'
# (the days to an event ahead)
FRONT_KINDS = ('top', 'liste', 'udvikling', 'citat', 'svar', 'live', 'linje', 'begivenhed', 'tal', 'nedtaelling')
FRONT_BLOCKS = 8     # blocks in a composition (the app draws no more); 6 until the event modules came (18/10)
FRONT_DRAWN = 6      # of which the app draws the first six (2026-10-17: overskuelighed før fuldstændighed)
FRONT_TOPS = 2       # 'top' blocks: one, two on a day with two main stories
FRONT_LIST = 8       # stories in one 'liste'
FRONT_TOPICS = 3     # developments in one 'udvikling' (the app shows three)
GREAT_OUTLETS, GREAT_SHOWN = 8, 6   # the input names the stories this widely carried that have no event page
GREAT_FIRST = 12    # the check calls for an update when a story this widely carried has come and no event page is kept
BLOCK_TITLE = 40     # characters of a block title
FRONT_LINE = 120     # characters of a 'linje'
LIST_STYLES = ('kompakt', 'billeder')
FRONT_STALE = timedelta(hours=6)   # the app's fixed front page takes over from an older composition (06-24)
TOP = 40         # top stories of the day listed for picks
RECAP_SHOWN = 5  # newest lines of each of today's topics in the input (the rest are counted)
OWNER_SHOWN = 15  # the owner's newest removals in the input
QUIET_UNTIL = 6  # Danish hour from which the day's updates run; before it only news of weight brings one
EVENING = 21     # Danish hour of the day's one notification: the first update at or after it
STALE = timedelta(hours=2)   # between 06 and 24 the front page is updated at least this often
RADAR_STILL = timedelta(minutes=30)   # the radar runs every 5 minutes: half an hour without a pass is a stop
FIRE_GAP = timedelta(minutes=15)      # the look is every quarter of an hour: one fire at most in each
UNDER_WAY = timedelta(minutes=30)     # a fire with no update since is an update under way for this long
EDITOR_FIRES = 12                     # fires of the routine a Danish day (config/settings.json editor_fires_per_day)
STALE_WIRE = 3                        # wire lines that make the two-hour reason hold without a story of weight
LEVEL_LAPSE = radar_level.STALE - timedelta(minutes=45)   # today's få/mange is renewed before the radar lets it lapse
CHECK_STORIES = 12   # stories of weight the check lists
CHECK_WIRE = 4       # newest wire lines the check shows
ANSWER_TEXT = 32000  # characters of a new answer's text in the input (the answers run to about 28,000)
ANSWER_KINDS = ('stilling', 'forhold', 'plan', 'fremgangsmåde', 'rolle', 'tilstand', 'motiv')
MAX_READINGS = 15
READING_LEN = 420
NOTE_LEN = 1200
SUBJECT_ID = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*(?:--[a-z0-9]+(?:-[a-z0-9]+)*)?$')
KEEP_WORD = 'keep'
FEEDS = json.loads((Path(__file__).resolve().parents[1] / 'config' / 'feeds.json').read_text(encoding='utf-8'))
DIGEST_FILES = ('digest.json', 'moves.json', 'summaries.json', 'answers.json', 'live.json', 'front.json', 'kalender.json',
                'events.json', 'memo.json', 'lessons.json', 'report.json', 'okonomi.json', 'owner.json', 'runs.json')
# the two editors' notes to each other (the owner, 18/10: the event editor looks at the front page four times a day, 'hvis
# den finder forbedringer skal den lave det og give besked til khabar hjernes næste kørsel om vurdering'): memo.json on
# the digest branch keeps the last MEMOS notes; the input shows those of the last MEMO_HOURS, and a new one from the event
# editor calls for an update; the owner reads the senior and chief editors' notes in his admin block (18/10), so a couple
# of days of them are kept
MEMOS, MEMO_HOURS, MEMO_TEXT = 20, 12, 1500
EDITORS = ('begivenhedsredaktør', 'forsideredaktør', 'chefredaktør', 'økonomiredaktør')
# the chief editor (the owner, 18/10: one editor once a day on the highest setting – 'ja sæt den op kl 5'): it reads the
# last day's own text (input --audit), keeps the fejlbog – rules drawn from the editors' mistakes, which every input shows
# at its top (lessons.json) – and writes the owner a short morning report (report.json, shown in the owner's admin block)
LESSONS_MAX, LESSON_TEXT, REPORT_TEXT = 40, 320, 4000
# the owner's comments (18/10, the owner: 'Giv mig også et felt hvor jeg kan skrive en kommentar til elementet til
# redaktørerne … alle elementer burde kunne holdes nede og få en "kommentar" valgmulighed'): the radar keeps them in
# removed.json `notes` on the data branch; the inputs list the open ones of the last OWNER_OPEN days, every editor may
# answer one (`owner_notes` in an update) and the answers are kept OWNER_KEEP days in owner.json on the digest branch,
# which the owner reads in his admin block. A comment on the answers or the wiki is not the editors' to act on (the
# owner's builder takes it), one on the Økonomi page the economy editor's, one on the calendar either's
OWNER_REPLY, OWNER_KEEP, OWNER_OPEN, OWNER_TITLES = 600, 14, 7, 12
# the editors' clocks in UTC hours, as their routines keep them (claude.ai/code/routines; the app's RUNS shows them in
# Danish time – keep the two alike): which editor an update comes from when it does not say, and the owner's overview of
# the runs (19/10, the owner: 'en widget på indstillinger for admin så jeg kan se hvad tid forskellige redaktører og andre
# automationer kører') – every update leaves a line in runs.json on the digest branch (who, when, what it did)
SCHEDULE = {'forsideredaktør': (5, 7, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22), 'begivenhedsredaktør': (6, 11, 19),
            'økonomiredaktør': (15,), 'chefredaktør': (4,)}
RUNS_KEPT = 120
LESSON_ID = re.compile(r'^[a-z0-9][a-z0-9-]{2,60}$')
CAL_KINDS = ('valg', 'topmøde', 'centralbank', 'frist', 'retssag', 'forhandling', 'dansk', 'andet')
CAL_KEEP = 2        # days an entry of the calendar stays after its day has passed
CAL_AHEAD = 30      # days of the calendar the input lists
CAL_MAX = 12        # entries one update may add or change
CAL_TITLE = 100     # characters of an entry's title
CAL_WHY = 200       # characters of its 'why'
MOVEMENT_GROUPS = ('bevægelsen', 'official')   # a line or quote from these sources gets the movement's checks too
WORK = Path(tempfile.gettempdir()) / 'editor'


def dk(t):
    """Danish local time (Europe/Copenhagen; EU summer-time rule where no time zone database is installed)."""
    try:
        from zoneinfo import ZoneInfo
        return t.astimezone(ZoneInfo('Europe/Copenhagen'))
    except Exception:  # noqa: BLE001
        def last_sunday(month):
            d = datetime(t.year, month, 31, 1, tzinfo=timezone.utc)
            return d - timedelta(days=(d.weekday() + 1) % 7)
        summer = last_sunday(3) <= t < last_sunday(10)
        return t.astimezone(timezone(timedelta(hours=2 if summer else 1)))


def ts(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00'))


def date_da(t, weekday=False):
    d = dk(t)
    return (f'{DAYS[d.weekday()]} ' if weekday else '') + f'{d.day}. {MONTHS[d.month - 1]} {d.year}'


def period_of(now):
    h = dk(now).hour
    return 'morgen' if h < 12 else 'eftermiddag' if h < 17 else 'aften'


def window_start(now, times=()):
    """Where an update's material begins: at the previous update (less than 20 hours old), so nothing falls between
    two updates; without one, 12 hours back."""
    earlier = [ts(t) for t in times if t and timedelta(0) < now - ts(t) < timedelta(hours=20)]
    return max(earlier) if earlier else now - timedelta(hours=12)


def clean(s):
    return ' '.join(str(s or '').split())


def clip(s, n):
    s = clean(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def kept(value):
    """A part the update leaves out, or marks "keep", stays as it is on the front page."""
    return value is None or (isinstance(value, str) and value.strip().casefold() == KEEP_WORD)


# the lede's parts, each of which opens its story on the front page (the owner, 17/10): cut where the clauses meet, a
# part of fewer than three words joined to its neighbour – the app's `ledeParts` (public/app.js); keep the two alike
LEDE_CUT = re.compile(r'(,\s+(?:og|mens)\s+|,\s+|;\s*|\s+–\s+|\s+mens\s+|\s+og\s+)')
LEDE_OPEN = re.compile(r'mens|;|–|,\s+og\s')


def lede_parts(text):
    """The lede's parts in order, as the app cuts them."""
    def words(s):
        return sum(1 for w in s.split() if re.search(r'[^\W_]', w))
    bits, out, held = LEDE_CUT.split(str(text or '').strip()), [], None   # out: [text, the separator before it]
    for k in range(0, len(bits), 2):
        part, sep = bits[k], bits[k - 1] if k else ''
        if held:   # a short subject after a clause's opening word, joined to its clause (as the app's ledeParts)
            part, sep, held = held[0] + sep + part, held[1], None
        if k and words(part) < 3 and LEDE_OPEN.search(sep) and k + 2 < len(bits) and re.fullmatch(r'\s+og\s+', bits[k + 1]):
            held = (part, sep)
            continue
        if out and words(part) < 3:
            out[-1][0] += sep + part
        else:
            out.append([part, sep])
    if len(out) > 1 and words(out[0][0]) < 3:
        out[:2] = [[out[0][0] + out[1][1] + out[1][0], '']]
    return [p for p, _ in out if p]


# ------------------------------------------------------------------ the day and the archive

def new_day(t):
    return {'date': dk(t).date().isoformat(), 'title': f'Politiske nyheder – {date_da(t)}', 'created': '',
            'updates': [], 'topics': [], 'ids': []}


def noon(date):
    """A moment safely inside a Danish calendar date, for naming its day."""
    return datetime(date.year, date.month, date.day, 11, tzinfo=timezone.utc)


def key(name):
    return ' '.join(str(name).split()).casefold()


def topic_of(day, name, section):
    """The day's topic of that name (the editor continues it by writing the name again), or a new one at the end."""
    for tp in day['topics']:
        if key(tp['name']) == key(name):
            return tp
    tp = {'name': ' '.join(str(name).split()), 'section': section, 'lines': []}
    day['topics'].append(tp)
    return tp


def newest_first(tp):
    tp['lines'].sort(key=lambda line: (line['at'], line['added']), reverse=True)


def main_topic(day):
    """Dagens historie's topic, as the app chooses it: the day's first topic with three lines or more."""
    return next((tp for tp in (day or {}).get('topics') or [] if len([x for x in tp.get('lines') or [] if x.get('at')]) >= 3), None)


def migrate(moves, data, lines):
    """Archives from before days existed hold editions ('briefs'): fold each into the day it was written on – a
    story becomes its headline, a statement stays as it was, and the wire lines it covered stay covered."""
    if 'days' in moves or not moves.get('briefs'):
        return moves
    when = {v['i']: v['p'] for v in lines.get('items', [])}
    when.update({i['id']: i.get('published') or i.get('found') for i in data.get('items', [])})
    days = {}
    for e in sorted(moves['briefs'], key=lambda e: e.get('created') or ''):
        if not e.get('created'):
            continue
        made = e['created']
        day = days.setdefault(dk(ts(made)).date().isoformat(), new_day(ts(made)))
        for tp in e.get('topics') or []:
            topic = topic_of(day, tp['name'], tp.get('section') or 'world')
            topic['lines'] += [{'who': '', 'text': s['headline'], 'link': s['link'], 'source': s['source'],
                                'at': when.get(s['id']) or made, 'added': made, 'id': s['id'], 'kind': 's',
                                **({'confirmed': 0} if s.get('confirmed') == 0 else {})} for s in tp.get('stories') or []]
            topic['lines'] += [{'who': x['who'], 'text': x['text'], 'link': x['link'], 'source': 'Al Jazeera',
                                'at': when.get(x['id']) or made, 'added': made, 'id': x['id'], 'kind': 'w'}
                               for x in tp.get('lines') or []]
            newest_first(topic)
        day['ids'] = sorted(set(day['ids']) | set(e.get('ids') or []))
        if 'ids' not in e:
            day['until'] = max(day.get('until', ''), e.get('until') or made)
        day['updates'].append(made)
        day['created'] = made
    return {'updated': moves.get('updated'), 'days': sorted(days.values(), key=lambda d: d['date'], reverse=True)}


# ------------------------------------------------------------------ reading the material

def read(args, ref, name, default):
    folder = args.dir or (getattr(args, 'data_dir', None) if ref == 'origin/data' else None)
    if folder:
        path = Path(folder) / name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    try:
        out = subprocess.run(['git', 'show', f'{ref}:{name}'], capture_output=True, check=True)
        return json.loads(out.stdout.decode('utf-8'))
    except subprocess.CalledProcessError:
        return default


def material(args):
    data = read(args, 'origin/data', 'data.json', {'items': []})
    lines = read(args, 'origin/data', 'lines.json', {'items': []})
    return data, lines, migrate(read(args, 'origin/digest', 'moves.json', {'days': []}), data, lines)


def summaries_of(args):
    return read(args, 'origin/digest', 'summaries.json', {'items': {}})


def answers_of(args):
    """Hizb ut-Tahrir's answers noted after the static layer (answers.json on the digest branch, kept forever)."""
    a = read(args, 'origin/digest', 'answers.json', {'items': {}})
    return {'items': dict(a.get('items') or {})} if isinstance(a, dict) else {'items': {}}


def waiting(args, noted):
    """Hizb ut-Tahrir's answers the radar fetched (analyses.json on the data branch) that neither the static layer
    (public/viden/movement-index.json) nor answers.json holds yet, newest first – only those with their text."""
    fetched = read(args, 'origin/data', 'analyses.json', {'items': []})
    items = fetched.get('items') if isinstance(fetched, dict) else fetched
    known = set(brain.static_answers()) | set(noted.get('items') or {})
    out = [a for a in items or [] if isinstance(a, dict) and a.get('id') and a.get('text') and str(a['id']) not in known]
    return sorted(out, key=lambda a: str(a.get('date') or ''), reverse=True)


def first_seen(args):
    """When the radar first found each article, and from which source (items.json on the data branch): a story's
    other articles carry their own time there, so a story that grew since the last update shows."""
    items = read(args, 'origin/data', 'items.json', {})
    if not isinstance(items, dict):
        return {}
    return {k: (v['found'], v.get('source') or k) for k, v in items.items() if isinstance(v, dict) and v.get('found')}


def big_outlets():
    try:
        return json.loads((ROOT / 'config' / 'settings.json').read_text(encoding='utf-8')).get('big_story_sources', 4)
    except (OSError, ValueError):
        return 4


def joined_since(i, seen, start):
    """How many outlets joined a story after `start`: the sources of its articles (its members, or the outlets'
    articles under 'also') that the radar found only after then – a second article from an outlet already there is
    no new outlet."""
    ids = set(i.get('members') or []) | {a['id'] for a in i.get('also') or [] if a.get('id')} | {i['id']}
    known = [seen[x] for x in ids if x in seen]
    before = {src for found, src in known if ts(found) < start}
    return len({src for found, src in known if ts(found) >= start} - before)


def articles(i, seen):
    """(found, id) of each of a story's articles the radar knows, the card's own lead included."""
    ids = set(i.get('members') or []) | {a['id'] for a in i.get('also') or [] if a.get('id')} | {i['id']}
    return [(ts(seen[x][0]), x) for x in ids if x in seen] + [(ts(i.get('found') or i['published']), i['id'])]


def story_key(i, seen):
    """A story's own id across passes: its first article's (a card's id is its lead's, which changes as outlets join)."""
    return min(articles(i, seen))[1]


def first_found(i, seen):
    """When the radar first found any of a story's articles: its card's lead changes when a bigger outlet joins, and the
    card's own 'found' is then the new lead's – the story itself is older (the review of 2026-10-17: a Houthi story found
    at 20.35 counted as new at 02.20 and again at 09.10)."""
    times = [t for t, _ in articles(i, seen)]
    first = (i.get('first') or {}).get('published')
    if first:
        try:
            times.append(ts(first))
        except ValueError:
            pass
    return min(times)


def fresh(items, since, seen, until=None):
    """The stories new since `since` (their first article found after it, and by `until`), and those that grew across a
    line since: big now with fewer outlets than a big story needs then, three outlets now with fewer then, or of tiers
    1-3 with two outlets now and one then. Each as (story, tier, outlets joined since, new)."""
    big = big_outlets()
    out = []
    for i in items:
        t = brain.tier_of(i)
        found = first_found(i, seen)
        if until and found > until:
            continue
        if found >= since:
            out.append((i, t, 0, True))
            continue
        joined = joined_since(i, seen, since)
        if not joined:
            continue
        n = i.get('outlets') or 1
        before = n - joined
        if (i.get('big') and before < big) or n >= 3 > before or (t is not None and t <= 3 and n >= 2 > before):
            out.append((i, t, joined, False))
    return out


def strongest(fresh_items, per_section, limit):
    """The strongest stories of each section first, then the rest by rank, each once, at most `limit`."""
    by_rank = sorted(fresh_items, key=lambda i: -(i.get('rank') or 0))
    first = [i for sec in SECTIONS for i in [x for x in by_rank if x.get('sec') == sec][:per_section]]
    out, seen = [], set()
    for i in first + by_rank:
        if i['id'] not in seen:
            seen.add(i['id'])
            out.append(i)
    return out[:limit]


def day_old(i, now):
    return now - ts(i.get('published') or i['found']) < timedelta(hours=24)


def to_summarise(items, done, now, opened=()):
    """The stories readers opened (the app's silent 'read' and 'copied' signals, learned.json), then the ones an
    opened card is most likely to be – the strongest of each section in the last day, then the rest by rank – those
    without a summary yet, at most MAX_SUM."""
    candidates = [i for i in items if day_old(i, now) and i['id'] not in done]
    read_ = [i for i in sorted(candidates, key=lambda i: -(i.get('rank') or 0)) if i['id'] in set(opened)]
    rest = strongest([i for i in candidates if i not in read_], 5, MAX_SUM)
    return (read_ + rest)[:MAX_SUM]


def recent_days(moves, now):
    """Today's day and yesterday's, as far as they exist: the two an update may add to."""
    today = dk(now).date()
    wanted = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    return [d for d in moves.get('days') or [] if d['date'] in wanted]


def update_times(moves):
    return [t for d in moves.get('days') or [] for t in d.get('updates') or []]


def last_update(moves, notes):
    """The time of the last full update: the newest an archived day lists, or the front page's own."""
    times = [ts(t) for t in update_times(moves) + [(notes or {}).get('created')] if t]
    return max(times) if times else None


def uncovered(lines, moves):
    """Every wire line no earlier update has looked at, oldest first. A day lists the lines its updates were given
    in `ids`; the very first editions kept no list and covered everything published up to their `until`."""
    done, upto = set(), ''
    for d in moves.get('days') or []:
        done.update(d.get('ids') or [])
        upto = max(upto, d.get('until') or '')
    wire = [v for v in lines.get('items', []) if v.get('k') == 'w' and v['i'] not in done
            and not (upto and ts(v['p']) <= ts(upto))]
    return sorted(wire, key=lambda v: v['p'])


def headline(i):
    return clean(i.get('title_da') or i.get('title_tr') or i.get('title'))


def teaser_of(i):
    return clean(i.get('summary_da') or i.get('summary_tr') or i.get('summary') or '')


def great_groups(pool, pages, now):
    """The widely carried stories of the last 36 hours that no event page holds, grouped by event (events.great_events)."""
    paged = {s for e in pages or [] for s in e.get('stories') or []}
    wide = [i for i in pool if (i.get('outlets') or 1) >= GREAT_OUTLETS and i['id'] not in paged
            and not set(i.get('members') or []) & paged
            and now - ts(i.get('published') or i.get('found')) < timedelta(hours=36)]
    return event_pages.great_events(wide, headline, GREAT_SHOWN)


# ------------------------------------------------------------------ Live: the admitted stories, their headlines, the level

def resolver(items):
    """Story id or member id -> the story (clusters merge, a card's lead changes: an id matches a story when it is the
    story's id or one of its members; a card's own id wins)."""
    out = {}
    for i in items:
        for m in i.get('members') or []:
            out.setdefault(m, i)
    out.update({i['id']: i for i in items})
    return out


def wire_stories(lines):
    """The wire's lines (lines.json: Al Jazeera's urgent one-liners) as stories an event page may cite for a count (18/10:
    the interior ministry's 2.397 arrested and 997 police injured came only by the wire, so the boxes could not take them
    while the recap did): the original line, its machine English and Danish; never a story the page lists."""
    labels = {**{f.get('name'): f.get('label') or f.get('name') for f in FEEDS}, **{f.get('label'): f.get('label') for f in FEEDS if f.get('label')}}
    out = {}
    for v in (lines or {}).get('items') or []:
        if v.get('i') and v.get('k') == 'w':
            name = re.sub(r'\s+(?:breaking|urgent|live)$', '', str(labels.get(v.get('s'), v.get('s') or 'Al Jazeera')), flags=re.I)
            out[v['i']] = {'id': v['i'], 'title': v.get('t') or '', 'title_tr': v.get('tr') or '', 'title_da': v.get('da') or '',
                           'summary': '', 'source': name, 'link': v.get('u') or '',
                           'published': v.get('p'), 'found': v.get('p'), 'wire': True}
    return out


def development(moves, now):
    """{recap topic name: its lines, newest first} for today and yesterday – an event page's development."""
    out = {}
    for d in sorted(recent_days(moves, now), key=lambda d: d['date'], reverse=True):
        for tp in d['topics']:
            out.setdefault(tp['name'], []).extend(tp['lines'])
    for k in out:
        out[k] = [{**x, 'hm': f"{dk(ts(x['at'])):%H.%M}" if x.get('at') else ''}
                  for x in sorted(out[k], key=lambda x: str(x.get('at') or ''), reverse=True)]
    return out


def behind_pages(pages, moves, now):
    """[(page, [(what, box or article, count, line, where)])] for the pages under way whose boxes or article count less
    than their own development."""
    dev = development(moves, now)
    out = []
    for e in pages or []:
        if e.get('status') == 'i gang' and e.get('topic'):
            lines = dev.get(e['topic']) or []
            gaps = [(*g, 'boksen') for g in event_pages.behind(e, lines)] + [(*g, 'artiklen') for g in event_pages.article_behind(e, lines)]
            if gaps:
                out.append((e, gaps))
    return out


def app_of(args):
    """The radar's slim app.json (the admitted stories the app shows), or None before the radar writes it."""
    a = read(args, 'origin/data', 'app.json', None)
    return a if isinstance(a, dict) and isinstance(a.get('items'), list) else None


def active_plan(live, now):
    """live.json as the radar reads it now (src/radar/level.py): the level it applies, and every take and drop still in
    force – the newest decision on a story wins, yesterday's too."""
    d = dk(now)
    return radar_level.plan(live or {}, d.date().isoformat(), d.hour, now)


def ids_of(i):
    return {i['id'], *(i.get('members') or [])}


def admitted(data, app, now, live=None):
    """(the admitted stories the app shows, known): the stories of app.json (as data.json holds them, when it does),
    else data.json's stories the radar marks `live`; before the radar draws the line (known False) every story of the
    last 48 hours, as the app shows today. live: live.json – a story the editor dropped is out at once, before the
    radar's next pass has applied it."""
    out, known = _admitted(data, app, now)
    if live:
        the_plan = active_plan(live, now)
        out = [i for i in out if radar_level.decision(the_plan, ids_of(i)) != 'drop']
    return out, known


def _admitted(data, app, now):
    items = data.get('items') or []
    if app is not None:
        find = resolver(items)
        out, seen = [], set()
        for a in app['items']:
            i = find.get(a.get('id')) or next((find[m] for m in a.get('members') or [] if m in find), None) or a
            if i.get('id') and (i.get('published') or i.get('found')) and i['id'] not in seen:
                seen.add(i['id'])
                out.append(i)
        return out, True
    if any('live' in i for i in items):
        return [i for i in items if i.get('live')], True
    return [i for i in items if now - ts(i.get('published') or i['found']) < timedelta(hours=48)], False


def the_line(data, app):
    """What the radar says of its line: {level, line (the rank threshold), count, …} from app.json or data.json's
    'live' (each optional)."""
    out = {}
    for src in (data.get('live'), (app or {}).get('live'), {k: (app or {}).get(k) for k in ('level', 'line', 'count')}):
        if isinstance(src, dict):
            out.update({k: v for k, v in src.items() if v is not None and k not in out})
    return out


def good_title(title):
    """True when a filed headline keeps today's rules (an earlier round's may not: a question, an analysis label, an
    op-ed's thesis)."""
    problems = []
    voice.check_headline(clean(title), 'title', problems)
    return bool(clean(title)) and not problems


def headed_ids(titles):
    """Every id the editor's headlines cover: the story ids they are filed under and the members filed with them – a
    headline that breaks the rules covers none (it is written again)."""
    out = set()
    for k, v in (titles or {}).items():
        if isinstance(v, dict) and not v.get('owner') and not good_title(v.get('title')):
            continue
        out.add(k)
        out.update((v or {}).get('members') or [] if isinstance(v, dict) else [])
    return out


def owner_state(args):
    """The owner's hand from the app as the radar keeps it (removed.json on the data branch)."""
    st = read(args, 'origin/data', 'removed.json', {})
    return st if isinstance(st, dict) else {}


def headlines_of(args):
    """The editors' headlines (summaries.json `titles`) with the owner's own over them (removed.json `titles`, 18/10: 'giv
    også en funktion der lader mig edit overskrifter direkte') – his words win in the app, the notifications and the
    archive, and a story he titled is no headline to write."""
    out = dict(summaries_of(args).get('titles') or {})
    for k, v in (owner_state(args).get('titles') or {}).items():
        if isinstance(v, dict) and v.get('t') and not k.startswith('ev:'):
            out[k] = {'title': v['t'], 'at': v.get('at'), 'owner': True}
    return out


def event_pictures(owner, items):
    """The owner's own picture of an event page (19/10, 'ev:<id>' among his pictures in removed.json): {page id: {pic,
    pf, pl}}, found among the stories' best pictures (data.json `pics`); a key no story holds any more is left out."""
    want = {k[3:]: v.get('k') for k, v in (owner.get('pics') or {}).items() if k.startswith('ev:') and isinstance(v, dict)}
    if not want:
        return {}
    found = {}
    for it in items:
        for p in it.get('pics') or []:
            if isinstance(p, dict) and p.get('k'):
                found.setdefault(p['k'], p)
    return {eid: {'pic': found[k].get('u'), 'pf': found[k].get('pf'), 'pl': found[k].get('pl')} for eid, k in want.items() if k in found}


def note_scope(ref):
    """Whose a comment is: 'okonomi' (the economy editor), 'kalender' (either), 'udvikler' (the answers and the wiki: no
    editor's) or 'redaktion' (the front-page and senior editors)."""
    r = str(ref or '')
    if r.startswith(('oko:', 'side:okonomi')):
        return 'okonomi'
    if r.startswith(('kal:', 'side:kalender')):
        return 'kalender'
    if r.startswith(('svar:', 'begreb:', 'side:analyses', 'side:svar', 'side:begreb')):
        return 'udvikler'
    return 'redaktion'


def owner_answers(args):
    a = read(args, 'origin/digest', 'owner.json', {'items': {}})
    return dict(a.get('items') or {}) if isinstance(a, dict) else {}


def open_notes(args, now, scopes):
    """The owner's comments of the last OWNER_OPEN days that no editor has answered, of the given scopes, oldest first."""
    done = owner_answers(args)
    out = []
    for n in owner_state(args).get('notes') or []:
        try:
            fresh = now - ts(n['at']) < timedelta(days=OWNER_OPEN)
        except (KeyError, TypeError, ValueError):
            continue
        if fresh and n.get('id') not in done and note_scope(n.get('ref')) in scopes:
            out.append(n)
    return sorted(out, key=lambda n: n['at'])


def note_target(ref, find, pages):
    """What a comment's reference names now, in a line for the editor (or '')."""
    parts = str(ref or '').split(':')
    if parts[0] == 'story' and len(parts) > 1:
        i = find(parts[1])
        return f"The story: [{parts[1]}] {clip(headline(i), 110)}" if i else f"The story [{parts[1]}] (no longer in the radar)"
    if parts[0] == 'ev' and len(parts) > 1:
        page = next((e for e in pages or [] if e.get('id') == parts[1]), None)
        part = ' · '.join(parts[2:])
        return (f"The event page {parts[1]}" + (f" ({clip(page.get('title'), 70)})" if page else ' (no longer kept)')
                + (f" – its {part}" if part else ''))
    if parts[0] == 'kal' and len(parts) > 1:
        return f"The calendar entry {parts[1]} (yours when its id begins with ed-; another you correct with an entry of your own on its day)"
    if parts[0] == 'oko':
        return f"The Økonomi page – {' · '.join(parts[1:]) or 'the page'}"
    return ''


def note_lines(notes, find, pages):
    """The input's open comments of the owner, with what each names now."""
    if not notes:
        return []
    out = ["## The owner's comments – open: do what he asks, then answer each in `owner_notes`", '',
           'He held an element in the app and wrote to you. Fix it in this update where you can – a headline, a summary, an',
           "event page, the calendar, the front page, the Økonomi page's lines – within every rule (reality only, every number",
           "from a cited story), and answer each comment in one or two plain Danish sentences: what you did (\"done\": true), or",
           "why it cannot be done here (\"done\": false – the app's layout, the page's figures and the wiki are not yours to",
           'change; say so plainly). What a comment teaches holds from now on: keep to it, and the chief editor writes it in the',
           'fejlbog. Fields: [id] when · where he held it and what it showed', '']
    for n in notes:
        out.append(f"[{n['id']}] {dk(ts(n['at'])):%d.%m %H.%M} · {clip(n.get('ctx') or n.get('ref'), 300)}")
        out.append(f"  The owner: {n.get('text')}")
        what = note_target(n.get('ref'), find, pages)
        if what:
            out.append(f'  {what}')
    return out + ['']


def note_history(args, now, find, pages, hours=36):
    """The chief editor's audit: every comment of the owner's of the last day and a half with the answer it got."""
    done = owner_answers(args)
    notes = [n for n in owner_state(args).get('notes') or [] if now - ts(n['at']) < timedelta(hours=hours)
             and note_scope(n.get('ref')) != 'udvikler']
    if not notes:
        return []
    out = ["## The owner's comments of the last day and a half, with the answers – draw the fejlbog's rules from them", '']
    for n in sorted(notes, key=lambda n: n['at']):
        a = done.get(n['id'])
        out.append(f"[{n['id']}] {dk(ts(n['at'])):%d.%m %H.%M} · {clip(n.get('ctx') or n.get('ref'), 200)}")
        out.append(f"  The owner: {n.get('text')}")
        out.append(f"  Answer ({a.get('by')}, {'done' if a.get('done') else 'not done'}): {a.get('text')}" if a else '  Not answered yet')
    return out + ['']


def owner_title_lines(args):
    """The owner's own headlines, newest first: his words win in the app; the editors learn his style from them."""
    titles = sorted(((k, v) for k, v in (owner_state(args).get('titles') or {}).items() if isinstance(v, dict) and v.get('t')),
                    key=lambda kv: kv[1].get('at') or '', reverse=True)[:OWNER_TITLES]
    if not titles:
        return []
    out = ["## The owner's own headlines – his words win in the app: never write another for these; learn his style", '',
           'Fields: the story id or event page · the headline the app showed → his', '']
    for k, v in titles:
        if k.startswith('ev:'):
            out.append(f"- event page {k[3:]} · \"{v.get('was') or '?'}\" → \"{v['t']}\" (write his as the page's title when you next change it)")
        else:
            out.append(f"- [{k}] · \"{v.get('was') or '?'}\" → \"{v['t']}\"")
    return out + ['']


def owner_file(entries, current, notes, now, problems):
    """owner.json as this update leaves it: the editors' answers to the owner's comments (`owner_notes`), each under its
    comment's id, the last OWNER_KEEP days kept; None when the update answers none."""
    if not entries:
        return None
    if not isinstance(entries, list):
        problems.append("owner_notes: a list of {\"id\": …, \"by\": …, \"reply\": …, \"done\": true|false}")
        return None
    known = {n.get('id'): n for n in notes or [] if isinstance(n, dict)}
    items = {}
    for k, v in ((current or {}).get('items') or {}).items():
        try:
            if isinstance(v, dict) and now - ts(v['at']) < timedelta(days=OWNER_KEEP):
                items[k] = v
        except (KeyError, TypeError, ValueError):
            continue
    for x in entries:
        if not isinstance(x, dict):
            problems.append('owner_notes: each answer is {"id", "by", "reply", "done"}')
            continue
        nid, text = str(x.get('id') or ''), ' '.join(str(x.get('reply') or '').split())
        if nid not in known:
            problems.append(f"owner_notes {nid or '?'}: no comment of the owner's has this id – copy it as the input gives it")
            continue
        if x.get('by') not in EDITORS:
            problems.append(f"owner_notes {nid}: 'by' is one of {', '.join(EDITORS)}")
            continue
        if not text:
            problems.append(f'owner_notes {nid}: the reply is missing – one or two Danish sentences to the owner')
            continue
        if len(text) > OWNER_REPLY:
            problems.append(f'owner_notes {nid}: {len(text)} characters – at most {OWNER_REPLY}')
        items[nid] = {'by': x['by'], 'text': text[:OWNER_REPLY], 'done': x.get('done') is not False,
                      'at': now.isoformat(timespec='seconds'), 'ref': known[nid].get('ref') or ''}
    return {'items': dict(sorted(items.items(), key=lambda kv: kv[1]['at'], reverse=True))}


def runner(draft, now):
    """Which editor wrote an update: the one its memo or its answers to the owner name; the chief editor's report and
    fejlbog, the economy editor's day; else the editor whose hour it is (UTC, SCHEDULE)."""
    named = [(draft.get('memo') or {}).get('by') if isinstance(draft.get('memo'), dict) else None,
             *[x.get('by') for x in draft.get('owner_notes') or [] if isinstance(x, dict)]]
    by = next((b for b in named if b in EDITORS), None)
    if by:
        return by
    if draft.get('report') or draft.get('lessons'):
        return 'chefredaktør'
    if draft.get('okonomi'):
        return 'økonomiredaktør'
    return next((b for b, hours in SCHEDULE.items() if now.hour in hours), 'forsideredaktør')


def run_note(draft):
    """What an update did, in a few Danish words for the owner's overview."""
    n = lambda k: len([x for x in draft.get(k) or [] if x]) if isinstance(draft.get(k), list) else 0  # noqa: E731
    lines = sum(len(t.get('lines') or []) for t in draft.get('topics') or [] if isinstance(t, dict))
    parts = []
    if draft.get('lede') and not kept(draft.get('lede')):
        parts.append('ny lede')
    if draft.get('front') and not kept(draft.get('front')):
        parts.append('forsiden')
    for k, one, many in (('titles', 'overskrift', 'overskrifter'), ('summaries', 'resumé', 'resuméer')):
        if n(k):
            parts.append(f"{n(k)} {one if n(k) == 1 else many}")
    if lines:
        parts.append(f"{lines} {'linje' if lines == 1 else 'linjer'} i udviklingen")
    for k, word in (('events', 'begivenheder'), ('calendar', 'kalenderen'), ('okonomi', 'Økonomi'), ('lessons', 'fejlbogen'),
                    ('report', 'rapporten'), ('owner_notes', 'svar til dig')):
        if draft.get(k):
            parts.append(word)
    return ', '.join(parts) or 'små rettelser'


def runs_file(current, by, did, now):
    """runs.json as this update leaves it: its line first, the last RUNS_KEPT kept."""
    items = [x for x in (current or {}).get('items') or [] if isinstance(x, dict)]
    return {'items': [{'by': by, 'at': now.isoformat(timespec='seconds'), 'did': did}, *items][:RUNS_KEPT]}


def has_head(i, done):
    return i['id'] in done or any(m in done for m in i.get('members') or [])


def waiting_since(i, record=None):
    """Since when an admitted story has waited for the editor's headline: when the radar first admitted it (its
    admitted.json on the data branch: member id -> when), else when its card was found."""
    times = []
    for x in {i['id'], *(i.get('members') or [])}:
        try:
            times.append(ts((record or {})[x]))
        except (KeyError, TypeError, ValueError):
            pass
    if times:
        return min(times)
    for f in ('admitted', 'found', 'published'):
        if i.get(f):
            try:
                return ts(i[f])
            except ValueError:
                continue
    return None


def to_head(pool, titles, now, record=None):
    """The admitted stories the app shows without the editor's headline – big ones first, then by rank – with how long
    each has waited (record: the radar's admitted.json)."""
    done = headed_ids(titles)
    out = [i for i in pool if not has_head(i, done)]
    # big stories first, then the ones the app shows worst (a curiosity headline, or only the machine's Danish), by rank
    poor = lambda i: bool(voice.curiosity(i.get('title'))) or i.get('lang') not in ('da', 'en')  # noqa: E731
    out.sort(key=lambda i: (not i.get('big'), not poor(i), -(i.get('rank') or 0)))
    return [(i, now - (waiting_since(i, record) or now)) for i in out]


def admitted_record(args):
    """The radar's admitted.json: member id -> when its story was first admitted to Live ({} before it exists)."""
    r = read(args, 'origin/data', 'admitted.json', {})
    return r if isinstance(r, dict) else {}


def day_level(live, now):
    """Today's entry of live.json ({} when the editor has set nothing today)."""
    return dict(((live or {}).get('days') or {}).get(dk(now).date().isoformat()) or {})


def in_24h(i, now):
    return now - ts(i.get('published') or i['found']) < timedelta(hours=24)


def in_48h(i, now):
    return now - ts(i.get('published') or i['found']) < timedelta(hours=48)


def around_the_line(data, pool, known, now, level, the_plan=None):
    """(the weakest admitted stories of the last 24 hours, the strongest left out), LINE_SHOWN each – big stories and the
    editor's takes are never at the line, and a story the editor dropped (today or yesterday) is not 'left out'."""
    if not known:
        return [], []
    inside = {i['id'] for i in pool}
    taken = set(level.get('take') or []) | set((the_plan or {}).get('take') or [])
    above = sorted((i for i in pool if in_24h(i, now) and not i.get('big') and i['id'] not in taken
                    and i.get('live') not in ('take', 'big', 'wide', 'dk')   # the radar's why: taken in or protected, not at it
                    and not taken & set(i.get('members') or [])), key=lambda i: i.get('rank') or 0)[:LINE_SHOWN]
    below = sorted((i for i in data.get('items') or [] if i['id'] not in inside and in_24h(i, now)
                    and radar_level.decision(the_plan or {}, ids_of(i)) != 'drop'),
                   key=lambda i: -(i.get('rank') or 0))[:LINE_SHOWN]
    return above, below


# ------------------------------------------------------------------ check: is there anything to adjust?

def ago(delta):
    m = int(delta.total_seconds() // 60)
    return f'{m} min' if m < 60 else f'{m // 60} t {m % 60:02d} min'


def weighty_big(r):
    """A big story calls for an update when it weighs: of tiers 1-10 by the books' order, or Danish (Danish politics is
    never buried) – a big story of the rest (tier 11) or weighed down (13) waits for the next update."""
    i, t = r[0], r[1]
    return bool(i.get('big')) and (t is None or t <= 10 or i.get('sec') == 'dk')


def head_reasons(now, heads):
    """The headline reasons: HEAD_WAIT admitted stories waiting for the editor's headline, or one waiting longer than
    HEAD_LATE between 06 and 24. heads: (story, waited) of the admitted stories without one."""
    if not heads:
        return []
    if len(heads) >= HEAD_WAIT:
        return [f'{len(heads)} historier i Live venter på redaktørens overskrift']
    oldest = max(w for _, w in heads)
    if oldest > HEAD_LATE and dk(now).hour >= QUIET_UNTIL:
        return [f'en historie i Live har ventet {ago(oldest)} på redaktørens overskrift']
    return []


def verdict(now, last, times, rows, answer, wire=(), covered=(), still=None, heads=(), lapse=None):
    """The reasons for a full update now, the most pressing first (empty: nothing of weight since the last). covered: the
    stories already a pick or in the recap – they call for no update of their own. still: how long the radar has not
    run, when that is longer than RADAR_STILL. heads: the admitted stories still without the editor's headline (with
    how long each has waited), when the radar draws the line."""
    reasons = []
    if still is not None:
        reasons.append(f'radaren står stille (sidst kørt for {ago(still)} siden)')
    rows = [r for r in rows if r[0]['id'] not in set(covered)]
    bigs = [r for r in rows if weighty_big(r)]
    if bigs:
        reasons.append(f'stor historie siden sidst: {clip(headline(bigs[0][0]), 80)}'
                       + (f' (+{len(bigs) - 1} mere)' if len(bigs) > 1 else ''))
    sharp = [r for r in rows if r[1] is not None and r[1] <= 3 and (r[0].get('outlets') or 1) >= 2 and not r[0].get('big')]
    if sharp:
        i, t = sharp[0][0], sharp[0][1]
        reasons.append(f"tier {t} med {i.get('outlets') or 1} medier: {clip(headline(i), 80)}"
                       + (f' (+{len(sharp) - 1} mere)' if len(sharp) > 1 else ''))
    if answer:
        reasons.append(f"nyt svar fra Hizb ut-Tahrir ({str(answer.get('date') or '')[:10]}) skal noteres")
    reasons += head_reasons(now, heads)
    if lapse:
        reasons.append(f'dagens niveau ({lapse}) holder kun {radar_level.STALE.seconds // 3600} timer efter sidste opdatering')
    d = dk(now)
    if d.hour >= QUIET_UNTIL:
        morning = d.replace(hour=QUIET_UNTIL, minute=0, second=0, microsecond=0)
        if last is None or dk(last) < morning:
            reasons.append(f'første kørsel efter kl. {QUIET_UNTIL}: dagens forside')
        elif now - last >= STALE and (rows or len(wire) >= STALE_WIRE):   # only when something changed
            reasons.append(f'{ago(now - last)} siden sidste opdatering')
        if d.hour >= EVENING and not any(dk(t).date() == d.date() and dk(t).hour >= EVENING for t in times):
            reasons.append(f'dagens resumé til telefonerne (første opdatering efter kl. {EVENING})')
    return reasons


def look(args, now):
    """What the quarter-hour look sees: (lines to print, reasons, facts for the gate)."""
    data, lines, moves = material(args)
    digest = read(args, 'origin/digest', 'digest.json', {})
    notes = digest.get('editor') or {}
    last = last_update(moves, notes)
    times = [ts(t) for t in update_times(moves) + [notes.get('created')] if t]
    since = last or now - timedelta(hours=12)
    items = data.get('items') or []
    news = fresh(items, since, first_seen(args), now)
    rows = sorted(((i, t, j, n) for i, t, j, n in news if (t is not None and t <= 5) or i.get('big') or (i.get('outlets') or 1) >= 3),
                  key=lambda r: (r[1] if r[1] is not None else 99, -(r[0].get('outlets') or 1), -(r[0].get('rank') or 0)))
    wire = uncovered(lines, moves)
    noted = answers_of(args)
    queue = waiting(args, noted)
    answer = next((a for a in queue if not last or not a.get('fetched') or ts(a['fetched']) > last), None)
    radar_at = ts(data['updated']) if data.get('updated') else None
    still = now - radar_at if radar_at and now - radar_at > RADAR_STILL else None
    notes_ = digest.get('editor') or {}
    picked = {p.get('id'): k for k, p in enumerate(notes_.get('picks') or [], 1)}
    recapped = {x['id'] for d in recent_days(moves, now) for tp in d['topics'] for x in tp['lines'] if x.get('kind') == 's'}
    app = app_of(args)
    live = read(args, 'origin/digest', 'live.json', {})
    pool, known = admitted(data, app, now, live)
    heads = to_head(with_economy(pool, args, items), headlines_of(args), now, admitted_record(args)) if known else []
    level = day_level(live, now)
    line = the_line(data, app)
    lapse = None   # today's få or mange lapses to normal when live.json is not written for radar_level.STALE (06-24)
    try:
        if level.get('level') in ('få', 'mange') and dk(now).hour >= QUIET_UNTIL and \
                now - ts(live.get('updated')) > LEVEL_LAPSE:
            lapse = level['level']
    except (TypeError, ValueError):
        pass
    out = [f'Khabar check · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time) · '
           + ((f'radar last ran {ago(now - radar_at)} ago' + (' – STOPPED' if still else '')) if radar_at else 'radar: no time'),
           f'Last full update: {dk(last):%d.%m %H.%M} ({ago(now - last)} ago)' if last else 'Last full update: none in the archive',
           f"New since {dk(since):%H.%M}: {sum(1 for r in news if r[3])} stories, {sum(1 for r in news if not r[3])} grew · "
           f"{len(rows)} of weight (tier 1-5, big or 3+ outlets) · {len(wire)} wire lines · "
           f"{'a new answer of Hizb ut-Tahrir' if queue else 'no new answer'}",
           live_line(level, line, pool, known, heads, now)]
    for i, t, joined, new in rows[:CHECK_STORIES]:
        grew = '' if new else f' (+{joined} since)'
        mark = f' = pick {picked[i["id"]]}' if i['id'] in picked else ' = in the recap' if i['id'] in recapped else ''
        out.append(f"  tier {t if t is not None else '?'} · {i.get('outlets') or 1} outlets{grew}{' · big' if i.get('big') else ''} · "
                   f"{i.get('sec')} · {dk(ts(i.get('published') or i['found'])):%H.%M} · {clip(headline(i), 110)}{mark}")
    if len(rows) > CHECK_STORIES:
        out.append(f'  (+{len(rows) - CHECK_STORIES} more of weight)')
    if wire:
        out.append(f'Newest wire lines ({min(CHECK_WIRE, len(wire))} of {len(wire)}):')
        out += [f"  {dk(ts(v['p'])):%H.%M} · {clip(v.get('da') or v.get('tr') or v.get('t'), 110)}" for v in wire[-CHECK_WIRE:][::-1]]
    if queue:
        a = queue[0]
        out.append(f"New answer waiting: nr {a['id']} · {str(a.get('date') or '')[:10]} · {clip(a.get('title'), 100)}")
    by_id = {i['id']: i for i in items}
    lede_at = notes.get('lede_at') or notes.get('created')
    out.append('Front page now:')
    out.append(f"  Lede ({dk(ts(lede_at)):%d.%m %H.%M}): {notes['lede']}" if notes.get('lede') and lede_at else '  Lede: none')
    front_now = read(args, 'origin/digest', 'front.json', {})
    out.append('  ' + composition_line(front_now, now))
    off = timeline_off(front_now, resolver(items), moves, digest)
    if off:
        out.append(f"  NOTE: Dagens historie's timeline '{off}' shares few words with its story – the app shows the story's "
                   'own development instead; name the topic the story belongs to')
    tp = main_topic(digest)
    out.append(f"  Dagens historie: {tp['name']} ({len(tp['lines'])} lines)" if tp else '  Dagens historie: none yet')
    picks = notes.get('picks') or []
    for k, p in enumerate(picks[:8], 1):
        i = by_id.get(p.get('id'))
        out.append(f"  Pick {k}: {clip(headline(i), 100) if i else '(no longer in the radar)'}")
    if not picks:
        out.append('  Picks: none')
    filed = [a for a in (noted.get('items') or {}).values() if str(a.get('date') or '') > wiki_built()[:10]]
    if filed:
        out.append(f"Note: {len(filed)} answer(s) filed after the wiki build (newest {filed[0].get('date')}) – the owner "
                   'rebuilds the wiki and reviews config/method.json powers (the app and the brain read them meanwhile)')
    reasons = verdict(now, last, times, rows, answer, wire, set(picked) | recapped, still, heads, lapse)
    memo_new = next((m for m in (read(args, 'origin/digest', 'memo.json', {}).get('items') or [])
                     if m.get('by') == EDITORS[0] and now - ts(m.get('at')) < timedelta(hours=MEMO_HOURS)), None)
    if memo_new:
        out.append(f"Note from the event editor ({dk(ts(memo_new['at'])):%H.%M}): {clip(memo_new.get('text'), 160)}")
    # a great event without its page (Begivenheder, 18/10): the widely carried stories grouped by event, and a group
    # whose words tell an event – not a decision or a statement – calls for an update, once
    pages = read(args, 'origin/digest', 'events.json', {}).get('items') or []
    great = next((g for g in great_groups(pool, pages, now) if g['word'] and g['outlets'] >= GREAT_FIRST), None)
    out.append(f"Event pages: {len(pages)}" + (f" · {sum(1 for e in pages if e.get('status') == 'i gang')} under way" if pages else ''))
    if great:
        lead = great['items'][0]
        reasons.append(f"stor begivenhed uden egen side: {clip(headline(lead), 80)} ({len(great['items'])} "
                       f"{'historie' if len(great['items']) == 1 else 'historier'}, op til {great['outlets']} medier)")
    # a page under way without its numbers while its stories carry them (18/10: the first page had none)
    find_ev = {**resolver([*pool, *items]), **wire_stories(lines)}.get   # a wire line is a source a box may cite
    thin_pages = event_pages.thin(pages, find_ev)
    # a page under way whose stories' articles carry counts it does not show (radar/reader.py): once for those counts
    fresh_counts = [] if thin_pages else event_pages.unused(pages, find_ev)[:1]
    for page, nums in fresh_counts:
        reasons.append(f"begivenhedssiden kan få nye tal fra artiklerne: {clip(page.get('title'), 60)} ({', '.join(nums[:4])})")
    for page, lacks in thin_pages[:1]:
        reasons.append(f"begivenhedssiden mangler {' og '.join(lacks)}: {clip(page.get('title'), 60)}")
    waiting_notes = open_notes(args, now, ('redaktion', 'kalender'))
    if waiting_notes:
        reasons.append(f"{len(waiting_notes)} {'kommentar' if len(waiting_notes) == 1 else 'kommentarer'} fra ejeren: "
                       f"{clip(waiting_notes[0].get('text'), 60)}")
    behind_now = behind_pages(pages, moves, now)[:1]
    for page, gaps in behind_now:
        reasons.append(f"begivenhedssidens tal er bagud for dens eget forløb: {clip(page.get('title'), 60)} ("
                       + '; '.join(f"{n} {what} mod {have if have is not None else 'ingen boks'} i {where}" for what, have, n, _, where in gaps[:3]) + ')')
    out.append(('OPDATÉR: ' + '; '.join(reasons)) if reasons else 'INTET NYT AF VÆGT')
    seen = first_seen(args)
    if great:
        facts_great = f"event:{story_key(great['items'][0], seen)}"
    else:
        facts_great = None
    keys = [f"big:{story_key(r[0], seen)}" for r in rows if weighty_big(r) and r[0]['id'] not in picked and r[0]['id'] not in recapped]
    keys += [f"tier:{story_key(r[0], seen)}" for r in rows if r[1] is not None and r[1] <= 3 and (r[0].get('outlets') or 1) >= 2
             and not r[0].get('big') and r[0]['id'] not in picked and r[0]['id'] not in recapped]
    if answer:
        keys.append(f"answer:{answer['id']}")
    if facts_great:
        keys.append(facts_great)
    if memo_new and (last is None or ts(memo_new['at']) > last):
        reasons.append('besked fra begivenhedsredaktøren')
        keys.append(f"memo:{memo_new['at']}")
    keys += [f"thin:{page['id']}:{page.get('at')}" for page, _ in thin_pages[:1]]
    keys += [f"counts:{page['id']}:{','.join(nums)}" for page, nums in fresh_counts]
    keys += [f"behind:{page['id']}:{','.join(str(g[2]) for g in gaps)}" for page, gaps in behind_now]
    keys += [f"note:{n['id']}" for n in waiting_notes]
    for r in head_reasons(now, heads):   # the headlines: once an update, or once for each story that waited too long
        if r[0].isdigit():
            keys.append(f"heads:{last.isoformat() if last else ''}")
        else:
            keys += [f'late:{story_key(i, seen)}' for i, w in sorted(heads, key=lambda h: -h[1]) if w > HEAD_LATE]
    if lapse:
        keys.append(f"level:{live.get('updated')}")
    facts = {'last': last, 'radar': radar_at, 'keys': keys, 'reasons': reasons}
    return out, reasons, facts


def live_line(level, line, pool, known, heads, now):
    """The check's line on Live: the day's level, how many stories are in, how many wait for the editor's headline."""
    lvl = level.get('level') or 'normal'
    told = f"level {lvl} ({'set by the editor' if level.get('level') else 'default'})"
    if not known:
        return f'Live: {told} · the radar draws no line yet ({sum(1 for i in pool if in_24h(i, now))} stories in 24 h)'
    n = sum(1 for i in pool if in_24h(i, now))
    at = f" · the radar's line: rank {line['line']}" if line.get('line') is not None else ''
    wait = (f" · {len(heads)} wait for a headline (longest {ago(max(w for _, w in heads))})" if heads
            else ' · every story has its headline')
    return f'Live: {told} · {n} admitted in 24 h{at}{wait}'


def composition_line(front, now):
    """The front page's composition in one line (the check)."""
    blocks = (front or {}).get('blocks') or []
    if not blocks or not front.get('updated'):
        return "Composition: none – the app's fixed front page"
    kinds = ', '.join(b.get('kind', '?') + (f" '{b['title']}'" if b.get('kind') == 'liste' and b.get('title') else '')
                      for b in blocks)
    old = ' – OLDER THAN 6 HOURS: the app shows its fixed page' if now - ts(front['updated']) > FRONT_STALE else ''
    return f"Composition ({dk(ts(front['updated'])):%d.%m %H.%M}): {kinds}{old}"


def timeline_off(front, find, moves, digest):
    """The first main block's timeline when it shares fewer than three words with its story (the app then shows the
    story's own development, pro-plan 3.2), else ''."""
    top = next((b for b in (front or {}).get('blocks') or [] if b.get('kind') == 'top' and b.get('timeline')), None)
    it = top and find.get(str(top.get('story') or ''))
    if not it:
        return ''
    days = [dayof for dayof in [digest] + list((moves or {}).get('days') or []) if isinstance(dayof, dict)]
    lines = [f"{l.get('who', '')} {l.get('text', '')}" for d in days for tp in d.get('topics') or []
             if key(tp.get('name', '')) == key(top['timeline']) for l in tp.get('lines') or []]
    words = voice.stems(' '.join([top['timeline'], *lines]))
    own = voice.stems(' '.join([top.get('title') or '', headline(it), it.get('title') or '',
                                *(a.get('title') or '' for a in it.get('also') or [])]))
    return top['timeline'] if len(words & own) < 3 else ''


def wiki_built():
    """When public/viden/begreber.json was built ('' when it is not there)."""
    return str(brain.load(brain.VIDEN / 'begreber.json', {}).get('built') or '')


def cmd_check(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    out, _, _ = look(args, now)
    print('\n'.join(out))


# ------------------------------------------------------------------ the gate: fire the routine only when it is needed

def fires_per_day():
    try:
        return int(json.loads((ROOT / 'config' / 'settings.json').read_text(encoding='utf-8')).get('editor_fires_per_day',
                                                                                                   EDITOR_FIRES))
    except (OSError, ValueError):
        return EDITOR_FIRES


def reason_keys(now, reasons, facts):
    """Each reason's key: a reason fires the routine once."""
    today = dk(now).date().isoformat()
    keys = list(facts.get('keys') or [])
    for r in reasons:
        if r.startswith('første kørsel efter'):
            keys.append(f'morning:{today}')
        elif r.startswith('dagens resumé'):
            keys.append(f'evening:{today}')
        elif r.endswith('siden sidste opdatering'):
            keys.append(f"stale:{facts['last'].isoformat() if facts.get('last') else ''}")
        elif r.startswith('radaren står stille'):
            keys.append(f"still:{facts['radar'].isoformat() if facts.get('radar') else ''}")
    return list(dict.fromkeys(keys))


def gate_decision(now, reasons, facts, state, ceiling):
    """(fire?, why) for one look. A reason fires once: a big or tier story, an answer, the morning and the evening each
    by its key; the two-hour reason by the update it is about. No fire while one is under way (fired less than
    UNDER_WAY ago with no update since), none within FIRE_GAP of the last, none past the day's ceiling – two kept for
    the morning's and the evening's – and between 00 and 06 only for a big story or a stopped radar."""
    if not reasons:
        return False, 'intet nyt af vægt'
    today = dk(now).date().isoformat()
    fired = [f for f in state.get('fires') or [] if f.get('day') == today and f.get('ok')]
    last_fire = max((ts(f['at']) for f in state.get('fires') or [] if f.get('ok')), default=None)
    last = facts.get('last')
    if last_fire and now - last_fire < UNDER_WAY and (last is None or last < last_fire):
        return False, f'opdatering i gang siden {dk(last_fire):%H.%M}'
    if last_fire and now - last_fire < FIRE_GAP:
        return False, f'affyret kl. {dk(last_fire):%H.%M} – næste kig om et kvarter'
    done = {k for f in state.get('fires') or [] if f.get('ok') for k in f.get('keys') or []}
    new = [k for k in reason_keys(now, reasons, facts) if k not in done]
    if not new:
        return False, 'grunden er set før – rutinen har vurderet den'
    if dk(now).hour < QUIET_UNTIL and not any(k.startswith(('big:', 'still:')) for k in new):
        return False, 'nat: kun en stor historie vækker redaktøren'
    if dk(now).hour < QUIET_UNTIL and any(dk(ts(f['at'])).hour < QUIET_UNTIL for f in fired):
        return False, 'nat: én opdatering om natten – resten venter til morgenen'
    reserved = (0 if any(k.startswith('morning:') for f in fired for k in f.get('keys') or []) else 1) + \
               (0 if any(k.startswith('evening:') for f in fired for k in f.get('keys') or []) else 1)
    special = any(k.startswith(('morning:', 'evening:', 'still:')) for k in new)
    if len(fired) >= ceiling or (not special and len(fired) >= ceiling - reserved):
        return False, f'dagens loft er nået ({len(fired)} af {ceiling})'
    # the day's fires spread over the day (06-24): by each hour at most its share of the ceiling, and one more
    d = dk(now)
    share = (ceiling - 2) * max(0.0, min(1.0, (d.hour + d.minute / 60 - QUIET_UNTIL) / (24 - QUIET_UNTIL)))
    plain = [f for f in fired if not any(k.startswith(('morning:', 'evening:', 'still:')) for k in f.get('keys') or [])]
    if not special and d.hour >= QUIET_UNTIL and len(plain) >= int(share) + 2:
        return False, f'dagens fyringer fordeles over dagen ({len(plain)} brugt kl. {d:%H.%M})'
    return True, '; '.join(reasons)


def fire(why):
    """One fire of the editor's routine through its API trigger (the routine's URL and token, GitHub secrets)."""
    import urllib.request
    url, token = os.environ.get('ROUTINE_FIRE_URL'), os.environ.get('ROUTINE_FIRE_TOKEN')
    if not url or not token:
        return False, 'ROUTINE_FIRE_URL or ROUTINE_FIRE_TOKEN is not set'
    body = json.dumps({'text': f'Kvarterets kig siger OPDATÉR: {why}'}).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01',
        'anthropic-beta': os.environ.get('ROUTINE_FIRE_BETA') or 'experimental-cc-routine-2026-04-01'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300, f'HTTP {r.status}'
    except Exception as e:  # noqa: BLE001 – a refused fire (the cap, a 429) is recorded, never fatal
        return False, f'{type(e).__name__}: {str(e)[:120]}'


def cmd_gate(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    out, reasons, facts = look(args, now)
    folder = Path(args.data_dir or args.dir or '.')
    path = folder / 'editor-gate.json'
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = {'fires': []}
    ok, why = gate_decision(now, reasons, facts, state, fires_per_day())
    print('\n'.join(out))
    if not ok:
        print(f'Gate: no fire – {why}')
        return
    keys, today = reason_keys(now, reasons, facts), dk(now).date().isoformat()
    sent, result = fire(why) if args.fire else (False, 'dry run (no --fire)')
    state['fires'] = [f for f in state.get('fires') or [] if now - ts(f['at']) < timedelta(days=3)] + [
        {'at': now.isoformat(timespec='seconds'), 'day': today, 'keys': keys, 'why': why, 'ok': sent, 'result': result}]
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"Gate: {'fired' if sent else 'not fired'} – {why} ({result})")


# ------------------------------------------------------------------ the input of a full update

TEMPLATE = {
    'memo': {'by': ' | '.join(EDITORS), 'text': '<optional – a note to your colleague: what you judged, changed and why, '
                                                   'what to keep or watch (at most 1500 characters)>'},
    'owner_notes': [{'id': "<an open comment of the owner's, its id as the input gives it (n…)>", 'by': ' | '.join(EDITORS),
                     'reply': '<one or two plain Danish sentences to the owner: what you did, or why it cannot be done here>',
                     'done': True}],
    'lede': '<one Danish sentence of at most about 25 words: the day so far, its heaviest movements first – reality only; '
            'leave the field out (or "keep") to keep the lede on the front page>',
    'lede_ids': ['<optional: the story id each part of the lede opens on the front page, one per part in order (the parts '
                 'are cut at ", ", " mens ", " og ", ";" and " – ", a part of fewer than three words joined to its '
                 'neighbour); "" for a part that names no story; leave out and the app finds the stories itself>'],
    'topics': [{
        'name': "<a topic of today's or yesterday's recap, written exactly as listed, or a new short concrete Danish heading>",
        'section': 'dk | me | world',
        'lines': [{'who': '<who says or reports it>', 'text': '<one short Danish sentence: what happened or was said>',
                   'story': '<the story id, when the line tells a story from the list>',
                   'ids': ['<the wire line id, when it comes from the wire>', '<a second id when two lines say the same>']}],
    }],
    'order': ['<the topic names of the day the lines went to, the weightiest first – the first with three lines or more is '
              'Dagens historie>'],
    'picks': [{'id': '<story id from the top stories, the weightiest first>', 'why': '<a few plain words: who acts, the tier>'}],
    'moves': [{'id': '<only a story in a clearly wrong section – rare; usually leave "moves" out>', 'sec': 'dk | me | world'}],
    'quotes': [{'who': '<speaker>', 'text': '<the statement in Danish, one or two sentences>', 'sec': 'dk | me | world',
                'ids': ['<wire line id>'], 'story': '<or a story id>',
                'okonomi': '<true for one statement on the economy – a central banker, a finance minister, the IMF: Økonomi shows it as its Dagens citat; else leave it out>'}],
    'titles': [{'id': '<story id from "Headlines to write">',
                'title': '<an informative Danish headline: who did or said what, where – a statement, never a teaser>'}],
    'summaries': [{'id': '<story id from "Stories to summarise">',
                   'text': '<2-3 Danish sentences from the headline, the teaser and the other outlets: what happened, who, why it matters>',
                   'paywall': True}],
    'level': 'få | normal | mange – how far down the ranking Live reaches today; leave out to keep',
    'take': ['<a story id from "Just below the line" (or any story) to take into Live today>'],
    'drop': ['<a story id in Live to take out today>'],
    'note': "<one line of reality: why today's level, e.g. 'Mange angreb og to topmøder'>",
    'front': {'lede': '<optional: the lede for the front page, when the update gives none above>',
              'lede_ids': ['<optional: as "lede_ids" above, for this lede>'],
              'blocks': [{'kind': 'top', 'story': '<id>', 'title': '<informative headline, optional>', 'with': ['<id>'],
                          'timeline': '<a recap topic name, optional>', 'picture': True},
                         {'kind': 'liste', 'title': "<block title, e.g. 'Danmark' or 'Krigen i Sudan'>",
                          'stories': ['<id>', '<id>'], 'style': 'kompakt | billeder'},
                         {'kind': 'udvikling', 'topics': ['<recap topic name>']},
                         {'kind': 'citat', 'quote': '<q1, q2 … – a quote of the front page, as listed>'},
                         {'kind': 'svar', 'nr': "<an answer of Hizb ut-Tahrir's that bears on today>"},
                         {'kind': 'live', 'n': 3},
                         {'kind': 'linje', 'text': '<one short line of reality>'},
                         {'kind': 'begivenhed', 'event': '<an event page id: its card with three key numbers, large>'},
                         {'kind': 'tal', 'event': '<an event page id>', 'fact': 1},
                         {'kind': 'nedtaelling', 'event': "<an event page ahead (status 'kommende'): the days to it>"}]},
    'events': [{'id': '<lowercase-with-hyphens, e.g. frankrig-uroligheder-2026-10; the same id changes a page, '
                      '{"id": …, "remove": true} takes it away>',
                'title': '<what is happening, in Danish: Uroligheder i Frankrig>', 'kicker': '<where or what: Frankrig>',
                'status': 'i gang | kommende | afsluttet', 'since': 'YYYY-MM-DD (i gang)', 'date': 'YYYY-MM-DD (kommende)',
                'dek': '<one factual line of what is happening and why it matters – reality, never a forecast>',
                'facts': [{'label': '<what is counted – a number of news value only, the event\'s size as a whole (the dead, the '
                                    'injured, the arrested, the marchers, the attacks counted); no such number: no boxes, "facts": []>',
                           'value': '<the number as the news give it: 1.800>',
                           'note': '<who says it: ifølge indenrigsministeren>', 'ids': ['<the stories the number stands in>'],
                           'was': {'value': '<optional – the earlier count, when it has grown: 1.200>',
                                   'when': '<when it was given: fredag>', 'ids': ['<the stories it stands in>']},
                           'of': '<optional – the whole a share is of: 10 for "7 af 10">'}],
                'places': ['<the places it happens in, the main one first: Paris>'],
                'map': {'km': '<optional – how many km the map shows at least each way; leave "map" out for the automatic frame>',
                        'focus': ['<optional – the places it frames>']},
                'quotes': [{'who': '<speaker>', 'text': '<the statement in Danish>', 'ids': ['<story id>']}],
                'stories': ['<its story ids in Live, the weightiest first>'], 'topic': '<a recap topic name: its timeline>',
                'article': [{'text': '<one paragraph told objectively, as a news agency tells it: what happened, who, where, '
                                     'when, the numbers and what was said, each fact with its first source – e.g. "Mere end '
                                     '1.800 mennesker er anholdt, oplyser Frankrigs indenrigsminister. Demonstranter stormede '
                                     'rådhuse i flere byer, og politiet satte tåregas ind." – never "X skriver"; facts, '
                                     'never opinion or forecast>', 'ids': ['<the stories it tells>']}]}],
    'calendar': [{'date': 'YYYY-MM-DD (or YYYY-MM with "approx": true)', 'title': '<what happens, in Danish: reality only>',
                  'kind': ' | '.join(CAL_KINDS), 'place': '<the country or city, optional>',
                  'why': '<one factual line: why it matters – never a forecast>', 'link': '<the source, optional with ids>',
                  'ids': ['<the story ids it comes from>']}],
}
CHIEF_TEMPLATE = {
    'lessons': [{'id': '<lowercase-with-hyphens; the same id changes a rule, {"id": …, "remove": true} takes it away>',
                 'rule': '<one plain rule the editors follow from now on, drawn from a mistake you found>',
                 'why': '<optional: the mistake it comes from, in a few words>'}],
    'report': '<the morning report to the owner, in Danish: what went well, what went wrong and what you changed; '
              'a few short paragraphs>',
}
ANSWER_TEMPLATE = {'answer': {
    'nr': "<the answer's number, as given>", 'date': 'YYYY-MM-DD',
    'title_da': '<the title in Danish, as the movement titles it: "Svar på spørgsmål: …">',
    'question_da': '<the question in one or two Danish sentences>',
    'note_da': '<2-4 plain Danish sentences, no "Ifølge …": what the answer reads and expects>',
    'readings': [{'subject': '<a subject id from the list, or a new lowercase-with-hyphens id; a relation: a--b>',
                  'kind': ' | '.join(ANSWER_KINDS), 'object': '<the other subject, e.g. the patron – optional>',
                  'value': '<a short label, e.g. underordnet – optional>',
                  'text_da': '<one plain Danish sentence of what it reads, no "Ifølge …">'}],
    'begreber': ['<the ids of the concepts, states and groups it treats>']}}
SMALL = [
    '## How small an update can be', '',
    'Leave out "lede", "picks" or "quotes" (or write "keep") and they stay as they are on the front page. An update may',
    'add only recap lines, or give only a new lede. Write a new lede when the weight of the day has changed – a story of',
    'a heavier tier, a development that moved – never only to vary the words; new picks when a heavier story has come.',
    '"moves" stay until undone (move the story back to its own section); "summaries" and "titles" are kept four days.',
    'Leave out "level", "take", "drop" and "note" and today\'s Live stays as it is (take and drop add to today\'s). Leave',
    'out "front" (or write "keep") and the composition stays as it is, its stories that left the radar dropped.',
    'Leave out "calendar" and the calendar stays; an entry stays until two days after its day (change it by its id,',
    'remove it with {"id": …, "remove": true}).', '',
]


def story_lines(i, joined=0):
    cover = ', '.join(f'{n} {k}' for k, n in (i.get('cover') or {}).items())
    flags = (' · big' if i.get('big') else '') + (' · kommentar' if i.get('kind') == 'kommentar' else '')
    t = brain.tier_of(i)
    tier = f' · tier {t}' if t is not None else ''
    grew = f' (+{joined} since the last update)' if joined else ''
    tr = i.get('title_tr')
    out = [f"[{i['id']}] {i.get('sec')}{tier} · rank {i.get('rank')}{flags} · {i.get('outlets', 1)} outlets{grew} ({cover}) · "
           f"confirmed {i.get('confirmed')}",
           f"{tr} (machine translation from {i.get('lang')}; original: {i['title']})" if tr else i['title']]
    summary = i.get('summary_tr') if tr else i.get('summary')
    if summary:
        out.append(summary)
    out.append(f"{i['source']} · {dk(ts(i.get('published') or i['found'])):%d.%m %H.%M} · {i['link']}")
    also = [f"{a['source']}: {a.get('title_tr') or a['title']}" for a in (i.get('also') or [])[:6]]
    if also:
        out.append('Also: ' + ' | '.join(also))
    return out + ['']


def memo_file(entry, current, now, problems):
    """memo.json as this update leaves it: the note added (by one of EDITORS, at most MEMO_TEXT characters), the last MEMOS
    kept; None when the update has no note."""
    if not entry:
        return None
    if not isinstance(entry, dict) or entry.get('by') not in EDITORS or not str(entry.get('text') or '').strip():
        problems.append(f"memo: {{'by': {' | '.join(EDITORS)}, 'text': '…'}} – a note to your colleague, or leave it out")
        return None
    text = re.sub(r'\s+', ' ', str(entry['text'])).strip()
    if len(text) > MEMO_TEXT:
        problems.append(f'memo: {len(text)} characters – at most {MEMO_TEXT}')
    items = [m for m in (current or {}).get('items') or [] if isinstance(m, dict)]
    return {'items': [{'at': now.isoformat(timespec='seconds'), 'by': entry['by'], 'text': text[:MEMO_TEXT]}, *items][:MEMOS]}


def lessons_file(entries, current, now, problems):
    """lessons.json as this update leaves it: the fejlbog's rules added, changed (same id) or removed ({id, remove}), at
    most LESSONS_MAX; None when the update names none."""
    if entries is None:
        return None
    items = {x['id']: x for x in (current or {}).get('items') or [] if isinstance(x, dict) and x.get('id')}
    if not isinstance(entries, list):
        problems.append('lessons: a list of {id, rule, why} – or leave it out')
        return None
    for k, x in enumerate(entries, 1):
        if not isinstance(x, dict) or not LESSON_ID.match(str(x.get('id') or '')):
            problems.append(f'lessons {k}: id – lowercase letters, digits and hyphens')
            continue
        if x.get('remove'):
            items.pop(x['id'], None)
            continue
        rule = re.sub(r'\s+', ' ', str(x.get('rule') or '')).strip()
        if not rule or len(rule) > LESSON_TEXT:
            problems.append(f"lessons {k} ({x['id']}): rule – one plain sentence or two (at most {LESSON_TEXT} characters)")
            continue
        old = items.get(x['id'], {})
        items[x['id']] = {'id': x['id'], 'rule': rule, **({'why': re.sub(r'\s+', ' ', str(x['why'])).strip()[:LESSON_TEXT]} if x.get('why') else {}),
                          'since': old.get('since') or dk(now).date().isoformat()}
    if len(items) > LESSONS_MAX:
        problems.append(f'lessons: {len(items)} rules – at most {LESSONS_MAX}: fold or remove the old ones')
    return {'updated': now.isoformat(timespec='seconds'), 'items': list(items.values())[:LESSONS_MAX]}


def lesson_lines(lessons):
    """The input's fejlbog: the chief editor's rules, which every editor follows."""
    items = (lessons or {}).get('items') or []
    if not items:
        return []
    out = ["## Fejlbogen – the chief editor's rules from earlier mistakes: follow every one", '']
    out += [f"- [{x['id']}] {x['rule']}" + (f" ({x['why']})" if x.get('why') else '') for x in items]
    return out + ['']


def report_file(text, now, problems):
    """report.json: the chief editor's morning report to the owner, or None."""
    if not text:
        return None
    t = str(text).strip()
    if len(t) > REPORT_TEXT:
        problems.append(f'report: {len(t)} characters – at most {REPORT_TEXT}')
    return {'at': now.isoformat(timespec='seconds'), 'text': t[:REPORT_TEXT]}


def audit_lines(args, now, find):
    """The last day's own text, for the chief editor's review: the headlines and summaries written, the outlet's own
    headline beside each."""
    s = summaries_of(args)
    since = now - timedelta(hours=26)
    titles = sorted(((k, v) for k, v in (s.get('titles') or {}).items() if isinstance(v, dict) and ts(v.get('at')) >= since),
                    key=lambda kv: kv[1].get('at') or '', reverse=True)[:120]
    sums = sorted(((k, v) for k, v in (s.get('items') or {}).items() if isinstance(v, dict) and ts(v.get('at')) >= since),
                  key=lambda kv: kv[1].get('at') or '', reverse=True)[:60]
    out = ['## Audit: the last day\'s own text (for your review)', '',
           f'### Headlines written ({len(titles)}) – yours ← the outlet\'s', '']
    for k, v in titles:
        it = find(k)
        own = headline(it) if it else ''
        out.append(f"[{k}] {dk(ts(v['at'])):%d.%m %H.%M} · {v['title']}" + (f"  ← {it.get('source')}: {own}" if it else ''))
    out += ['', f'### Summaries written ({len(sums)})', '']
    out += [f"[{k}] {dk(ts(v['at'])):%d.%m %H.%M} · {v.get('text')}" for k, v in sums]
    return out + ['']


def memo_lines(memo, now):
    """The input's notes from the editors of the last MEMO_HOURS, newest first."""
    notes = [m for m in (memo or {}).get('items') or [] if now - ts(m.get('at')) < timedelta(hours=MEMO_HOURS)]
    if not notes:
        return []
    out = ["## Notes between the editors – read the other editor's first: keep what it set unless the news moved since", '']
    out += [f"- {dk(ts(m['at'])):%d.%m %H.%M} · {m.get('by')}: {m.get('text')}" for m in notes]
    return out + ['']


def front_lines(notes, digest, by_id):
    """The front page as it is now, so an update can keep what still holds."""
    out = ['## The front page now – keep what still holds', '']
    lede_at = notes.get('lede_at') or notes.get('created')
    out.append(f"Lede (written {dk(ts(lede_at)):%d.%m %H.%M}): {notes['lede']}" if notes.get('lede') and lede_at else 'Lede: none yet')
    if notes.get('lede'):   # each part opens a story on the front page ("lede_ids": one id per part)
        ids = notes.get('lede_ids') or []
        out.append('Lede parts: ' + ' | '.join(f'{k}. {x}' + (f' = [{ids[k - 1]}]' if k <= len(ids) and ids[k - 1] else '')
                                              for k, x in enumerate(lede_parts(notes['lede']), 1)))
    tp = main_topic(digest)
    out.append(f"Dagens historie: {tp['name']}" if tp else 'Dagens historie: none yet (the first topic with three lines becomes it)')
    for k, p in enumerate([p for p in notes.get('picks') or [] if p.get('id') in by_id], 1):
        i = by_id[p['id']]
        t = brain.tier_of(i)
        out.append(f"Pick {k}: [{i['id']}]{f' tier {t} ·' if t is not None else ''} {clip(headline(i), 110)}")
    out.append(f"Quotes: {len(notes.get('quotes') or [])} · moves: {len(notes.get('moves') or [])}")
    return out + ['']


def head_lines(heads, known, listed=()):
    """The admitted stories still without the editor's headline, each with the outlet's headline and teaser and the
    other outlets' headlines (a story the input listed above already: only its headline) – at most MAX_TITLES, the
    strongest first."""
    if not heads:
        return []
    shown = heads[:MAX_TITLES]
    out = [f'## Headlines to write – {len(shown)}' + (f' of {len(heads)}' if len(heads) > len(shown) else '')
           + (' (the stories in Live without your headline, the strongest first)' if known
              else " (the day's strongest stories without your headline)"), '',
           'The app shows your headline for every story – Danish outlets too – instead of the outlet\'s. Write each as a news',
           'wire would: who did or said what, where (when, if it matters) – a statement that gives the news, never a teaser.',
           "No question, no 'Derfor …', 'Se …', 'Her er …', 'Sådan …', 'Det skal du vide', no cliff-hanger colon or '…' at the",
           "end ('Who: what' is fine: 'Kreml: Samtalerne fortsætter'). Only the facts the outlet's headline, its teaser and the",
           "other outlets' headlines support; the source's own loaded words kept where they carry its framing; names in their",
           'usual Danish spelling (Zelenskyj, Netanyahu, Hizbollah); at most about 110 characters. Example: "Se billederne: Kaos',
           'i lufthavnen" → "Houthi-angreb lukker King Khalid-lufthavnen i Riyadh; 12 dræbt". An informative headline may stay',
           "as it is (in Danish). The headline states the news of the outlet's article listed first – the one the app opens",
           "under 'Læs' – not another outlet's angle. No judgement of your own ('egentlige', 'reelle', 'i virkeligheden') and no",
           "'– video' at the end. A headline of yours that broke these rules is listed again: write it anew.", '',
           'Fields: [id] section · outlet (language) · waited · headline (the machine\'s Danish) · teaser · other outlets', '']
    for i, waited in shown:
        t = brain.tier_of(i)
        da = i.get('title_da') if i.get('lang') != 'da' and i.get('title_da') else ''
        out.append(f"[{i['id']}] {i.get('sec')}{f' · tier {t}' if t is not None else ''}{' · big' if i.get('big') else ''} · "
                   f"{i.get('source')} ({i.get('lang') or '?'}) · {i.get('outlets') or 1} outlets"
                   + (f' · waited {ago(waited)}' if known and waited > timedelta(0) else ''))
        out.append(f"  {clean(i.get('title'))}" + (f" (English: {clean(i['title_tr'])})" if i.get('title_tr') else '')
                   + (f' → {clean(da)}' if da else ''))
        if i['id'] in listed:
            out.append('  (teaser and other outlets: listed above)')
            continue
        teaser = i.get('summary_tr') if i.get('title_tr') else i.get('summary')
        if clean(teaser):
            out.append(f'  Teaser: {clip(teaser, TEASER)}')
        others = [f"{a.get('source')}: {clip(a.get('title_tr') or a.get('title'), 90)}" for a in (i.get('also') or [])[:OTHERS]]
        if others:
            out.append('  Others: ' + ' | '.join(others))
    return out + ['']


def story_row(i):
    t = brain.tier_of(i)
    return (f"[{i['id']}] {i.get('sec')}{f' · tier {t}' if t is not None else ''} · rank {i.get('rank')} · "
            f"{i.get('outlets') or 1} outlets{' · kommentar' if i.get('kind') == 'kommentar' else ''} · {clip(headline(i), 110)}")


def live_lines(level, line, above, below, pool, known, now, the_plan=None):
    """How much Live holds today, and the candidates at the radar's line: the editor's level, take and drop."""
    lvl = level.get('level')
    out = ['## Live – how much the app shows today (you decide)', '',
           f"Today's level: {lvl or 'normal'}" + (f' (yours: {level["note"]})' if lvl and level.get('note') else
                                                  ' (yours)' if lvl else ' (the default – not set today)')
           + (f" · taken in: {', '.join(level['take'])}" if level.get('take') else '')
           + (f" · taken out: {', '.join(level['drop'])}" if level.get('drop') else '')]
    still = {f: sorted(set((the_plan or {}).get(f) or ()) - set(level.get(f) or [])) for f in ('take', 'drop')}
    if still['take'] or still['drop']:   # yesterday's decisions still hold (a take or drop today undoes one)
        out.append('Still in force from yesterday:' + (f" taken in {', '.join(still['take'])}" if still['take'] else '')
                   + (';' if still['take'] and still['drop'] else '')
                   + (f" taken out {', '.join(still['drop'])}" if still['drop'] else ''))
    n = sum(1 for i in pool if in_24h(i, now))
    if known:
        bits = [f'{n} stories in Live from the last 24 hours']
        if line.get('line') is not None:
            bits.append(f"the radar's line at rank {line['line']}"
                        + (f" (the level's floor {line['floor']})" if line.get('floor') not in (None, line['line']) else ''))
        if line.get('count') is not None:
            bits.append(f"the level's soft count {line['count']}")
        if line.get('level') and line['level'] != (lvl or 'normal'):
            bits.append(f"the radar applies {line['level']}" + (f" ({line['why']})" if line.get('why') else ''))
        out.append(' · '.join(bits))
    else:
        out.append(f'The radar does not draw the line yet: the app shows all {n} stories of the last 24 hours.')
    out += ['', 'The level sets how far down the brain\'s ranking Live reaches for the last 24 hours:',
            f'"få" (a quiet day, only the sharpest – about {LEVEL_SIZE["få"]}), "normal" (the day\'s most important – about '
            f'{LEVEL_SIZE["normal"]}),',
            f'"mange" (a day of many strong stories – about {LEVEL_SIZE["mange"]}). A quiet day is never padded. The radar',
            'applies it at its next pass (within five minutes) and holds it for the Danish day – through the night until',
            f'your first update of the next – as long as you update at least every {radar_level.STALE.seconds // 3600} hours '
            '(else it falls back to "normal");',
            'big stories and Danish politics on Islam, Muslims, integration and foreign policy are never cut. "take" brings',
            'one story in, "drop" takes one out – even a big story – for today and tomorrow (your newest decision on a',
            'story wins). "note": one line of reality, why the level. Give every story you take in a headline too.', '']
    if above:
        out += ['Just above the line (the weakest in Live – drop one that is no news):'] + [story_row(i) for i in above] + ['']
    if below:
        out += ['Just below the line (the strongest left out – take one that matters):'] + [story_row(i) for i in below] + ['']
    return out


def front_section(front, find, notes, now):
    """The front page's composition now, the palette and a short guide to the owner's taste."""
    out = ['## The front page – your composition ("front")', '']
    blocks = (front or {}).get('blocks') or []
    if blocks and front.get('updated'):
        old = now - ts(front['updated']) > FRONT_STALE
        out.append(f"Now (composed {dk(ts(front['updated'])):%d.%m %H.%M}"
                   + (', older than 6 hours: the app shows its fixed page' if old else '') + '):')
        name = lambda x: f"[{x}] {clip(headline(find[x]), 70)}" if x in find else f'[{x}] (no longer in the radar)'  # noqa: E731
        for k, b in enumerate(blocks, 1):
            kind = b.get('kind')
            if kind == 'top':
                desc = name(b.get('story')) + (f" · title: {b['title']}" if b.get('title') else '') \
                    + (f" · with {', '.join(name(x) for x in b.get('with') or [])}" if b.get('with') else '') \
                    + (f" · timeline: {b['timeline']}" if b.get('timeline') else '') + ('' if b.get('picture', True) else ' · text lead')
            elif kind == 'liste':
                desc = f"'{b.get('title')}' ({b.get('style') or 'kompakt'}): " + '; '.join(name(x) for x in b.get('stories') or [])
            elif kind == 'udvikling':
                desc = ', '.join(b.get('topics') or [])
            elif kind == 'citat':
                desc = f"{b.get('quote')}: {b.get('who')}: {clip(b.get('text'), 80)}"
            elif kind == 'svar':
                desc = f"nr {b.get('nr')}"
            elif kind == 'live':
                desc = f"the {b.get('n', 3)} newest"
            else:
                desc = clean(b.get('text'))
            out.append(f'{k}. {kind}' + (f" '{b['title']}'" if b.get('title') and kind not in ('top', 'liste') else '') + f' · {desc}')
    else:
        out.append("Now: no composition – the app shows its fixed front page (lede, Dagens historie, Døgnets vigtigste, Følg "
                   'udviklingen, Dagens citat, Live).')
    quotes = notes.get('quotes') or []
    if quotes:
        out.append('Quotes for a "citat" block (the front page\'s now; when this update sends "quotes", q1, q2 … are its own): '
                   + ' | '.join(f"q{k}: {q.get('who')}: {clip(q.get('text'), 60)}" for k, q in enumerate(quotes, 1)))
    out += ['', f'The palette, in any order you choose (the app draws {FRONT_DRAWN} blocks – compose at most that many; a',
            'story in one block only; ids from this input):',
            '- top: the day\'s main story – its title (your informative headline), one related story in "with" (the app',
            '  shows one), the recap topic whose lines are its timeline (the app shows its two newest). Dagens historie',
            '  shows its story\'s own picture above the headline; "picture": false gives a second main story a text lead.',
            '  Once, or twice on a day with two main stories.',
            '- liste: a titled group of stories (2-8), "style" kompakt (rows with small pictures) or billeder; the app shows',
            '  the first three (the rest behind "Alle"), so put the weightiest first.',
            f'- udvikling: recap topics (1-{FRONT_TOPICS}) that moved – the developments to follow.',
            '- citat: one quote of the front page (q1, q2 …).',
            "- svar: an answer of Hizb ut-Tahrir's (its number) that bears on today – shown as theirs, attributed.",
            '- live: the n newest stories in Live (1-10).',
            "- linje: one short line of reality (at most 120 characters), e.g. '14 nye angreb på Riyadh i dag'.",
            'The owner\'s taste: compact, overskuelighed før fuldstændighed, few kinds of information per row; block titles short',
            'and concrete, never like a day marker (no "I dag", no dates). Denmark only when it matters: a Danish block or',
            'story only for a big Danish story, Danish policy on Islam and Muslims, or Denmark\'s place in a great power\'s',
            'plan – else at most a short block late on the page (the app cuts a Danish list of no such weight to two rows and',
            'sets it last). The rest is your own editorial taste and the brain: what leads, how many blocks, what each is',
            'called. Every word is reality.',
            'Send "front" when the day\'s weight or its stories changed; leave it out to keep the composition (re-dated).', '']
    return out


def answer_lines(a, known):
    """Hizb ut-Tahrir's new answer, with its text and how to note it."""
    date = str(a.get('date') or '')[:10]
    return [
        '## Hizb ut-Tahrir\'s new answer – note it in "answer" (once: it is kept for the concept pages)', '',
        f"nr {a['id']} · {date} · {clean(a.get('title'))} · {a.get('url') or ''}", '',
        'Write the "answer" object (shape below) from this text. Everything in it is what the answer says, its reading as '
        'it says it – never your own: note_da (2-4 sentences: what the answer reads and expects) and every reading in '
        'plain Danish without "Ifølge Hizb ut-Tahrirs svar …" or "Ifølge svaret …" (the app shows them under the label '
        '"Hizb ut-Tahrirs svar · d/m/åååå"): "Saudi-Arabien er underordnet USA", not "Ifølge svaret er Saudi-Arabien '
        'underordnet USA". The newest answer governs: where it reads a state, a power or a relation differently from its current reading in the brain, '
        'the reading says so plainly ("… vender tilbage til …", "… er faldet fra …"). One reading per subject the answer '
        'reads – kind stilling (a standing: value underordnet, satellit, uafhængig …, object the patron), forhold (a '
        'relation: subject a pair a--b), plan, fremgangsmåde (a means), rolle, tilstand (a power\'s condition or the '
        'international situation) or motiv; "begreber": the ids of the concepts, states and groups it treats.',
        'The rules hold here too: Israel by its name (the answer\'s "den jødiske entitet" only inside a short quotation); no '
        'praise of or call to violence; judge states, rulers, policies and ideas – never peoples or religions; '
        '"underordnet" or "satellit", never "agent"; no claim that a non-ruling person, a Danish person or organisation, a '
        'mosque, a scholar or a media outlet serves anyone; where the answer says a deadly attack was staged or planned by a '
        'power, write "gerningsbelæg mangler" or leave it out; quotations at most 60 characters (all of it is public).', '',
        'Subject ids to use where they fit (a new one: lowercase-with-hyphens; a relation: a--b in alphabetical order): '
        + ', '.join(sorted(k for k in known if '--' not in k)), '',
        "### The answer's text", '', str(a.get('text') or '')[:ANSWER_TEXT], '']


def econ_stories(items, now, hours=36):
    """The economic stories of the last `hours` – the Økonomi page's own patterns (oil, fuel and gas; debt, central
    banks, tariffs, sanctions, markets) on every headline the radar has of a story –, strongest first."""
    out = []
    for i in items:
        text = ' '.join(str(x) for x in (i.get('title'), i.get('title_tr'), i.get('title_da'),
                                         *[a.get('title') for a in i.get('also') or []]) if x)
        if now - ts(i.get('published') or i['found']) < timedelta(hours=hours) and (
                radar_energy.NEWS.search(text) or radar_energy.CRISIS.search(text) or econ.MARKETS.search(text)):
            out.append(i)
    return sorted(out, key=lambda i: -(i.get('rank') or 0))[:ECON_STORIES]


ECON_STORIES = 40


def titled_by(args, draft):
    """Whether a story has the editor's Danish headline – kept, or given in this update (by any of its articles)."""
    kept = summaries_of(args).get('titles') or {}
    have = set(kept) | {m for v in kept.values() if isinstance(v, dict) for m in v.get('members') or []}
    have |= {str(x.get('id')) for x in draft.get('titles') or [] if isinstance(x, dict) and x.get('id')}
    return lambda it: bool({it['id'], *(it.get('members') or []), *(a.get('id') for a in it.get('also') or [] if a.get('id'))} & have)


def economy_shown(args, items):
    """The stories the Økonomi page shows or holds back for want of the editor's headline – energy.json's oil and fuel
    news, its finance news and the economy editor's stories under each topic –, those not from a Danish outlet: their
    headline is the editors' to write (19/10, the owner: 'Økonomi sidens nyhedshistorie titel oversættelser er elendige
    og bør gennemrettes af redaktøren inden udgivelse')."""
    d = read(args, 'origin/data', 'energy.json', {}) or {}
    ids = [n.get('i') for k in ('news', 'crisis') for n in d.get(k) or [] if isinstance(n, dict)]
    ids += [n.get('i') for v in ((d.get('ed') or {}).get('emner') or {}).values() if isinstance(v, dict)
            for n in v.get('news') or [] if isinstance(n, dict)]
    find, out, seen = resolver(items), [], set()
    for i in ids:
        it = find.get(i) if i else None
        if it and it['id'] not in seen and it.get('lang') != 'da':
            seen.add(it['id'])
            out.append(it)
    return out


def with_economy(pool, args, items):
    """The pool whose headlines the editors write: Live's stories and the Økonomi page's (economy_shown)."""
    have = {i['id'] for i in pool}
    return [*pool, *(i for i in economy_shown(args, items) if i['id'] not in have)]


def econ_input(args, now):
    """The economy editor's input (input --okonomi): the fejlbog and the notes, the brain, the page's figures, the
    economic news, the stories among them still without a headline, the fortnight ahead in the calendar and the dates
    the news name, the page as the last economy update left it."""
    data, _, _ = material(args)
    items = data.get('items', [])
    noted = answers_of(args)
    stories = econ_stories(items, now)
    out = [f'# Material for the economy update · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time)', '']
    out += lesson_lines(read(args, 'origin/digest', 'lessons.json', {}))
    out += memo_lines(read(args, 'origin/digest', 'memo.json', {}), now)
    out += note_lines(open_notes(args, now, ('okonomi', 'kalender')), resolver(items).get,
                      read(args, 'origin/digest', 'events.json', {}).get('items') or [])
    out += owner_title_lines(args)
    out += brain.section(stories[:TOP], noted['items'])
    cal_now, kal_now = read(args, 'origin/data', 'calendar.json', {}), read(args, 'origin/digest', 'kalender.json', {})
    out += econ.input_lines(read(args, 'origin/data', 'energy.json', {}), stories, read(args, 'origin/digest', 'okonomi.json', {}),
                            cal_now, kal_now, now, story_lines)
    titles = headlines_of(args)
    # the stories the page shows, too; to_head gives (story, how long it waited) – the filter that once compared those
    # pairs with the stories let none through, so the economy editor never had a headline to write (19/10)
    heads = to_head(with_economy(stories, args, items), titles, now)
    out += head_lines(heads, True, {i['id'] for i in stories})
    out += calendar_lines(cal_now, kal_now, now)
    heads_now = {k: (v.get('title') if isinstance(v, dict) else v) for k, v in (titles or {}).items()}
    out += news_dates(stories, cal_now, kal_now, now, heads_now)
    template = {**econ.TEMPLATE, **{k: TEMPLATE[k] for k in ('titles', 'summaries', 'calendar', 'memo', 'owner_notes') if k in TEMPLATE}}
    out += ['', '## Write /tmp/editor/update.json in exactly this shape (UTF-8 JSON)', '',
            json.dumps(template, ensure_ascii=False, indent=1)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'input.md').write_text('\n'.join(out), encoding='utf-8')
    (WORK / 'input.meta').write_text(json.dumps({'digest': '' if args.dir else digest_head(), 'made': now.isoformat()}),
                                     encoding='utf-8')
    print(f'{WORK / "input.md"}: {len(stories)} economic stories, {len(heads)} without a headline')


def cmd_input(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    if getattr(args, 'okonomi', False):
        econ_input(args, now)
        return
    data, lines, moves = material(args)
    digest = read(args, 'origin/digest', 'digest.json', {})
    notes = digest.get('editor') or {}
    start = window_start(now, update_times(moves))
    told = {x['id'] for d in recent_days(moves, now) for tp in d['topics'] for x in tp['lines'] if x.get('kind') == 's'}
    items = data.get('items', [])
    by_id = {i['id']: i for i in items}
    news = [(i, j) for i, _, j, _ in fresh(items, start, first_seen(args), now) if i['id'] not in told]
    news.sort(key=lambda x: -(x[0].get('rank') or 0))
    top = sorted((i for i in items if now - ts(i.get('published') or i['found']) < timedelta(hours=24)),
                 key=lambda i: -(i.get('rank') or 0))[:TOP]
    wire = uncovered(lines, moves)
    noted = answers_of(args)
    out = [f'# Material for the {dk(now):%H.%M} update · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time)', '']
    out += lesson_lines(read(args, 'origin/digest', 'lessons.json', {}))
    out += memo_lines(read(args, 'origin/digest', 'memo.json', {}), now)
    pages_now = read(args, 'origin/digest', 'events.json', {}).get('items') or []
    out += note_lines(open_notes(args, now, ('redaktion', 'kalender')), resolver(items).get, pages_now)
    out += owner_title_lines(args)
    if getattr(args, 'audit', False):
        out += audit_lines(args, now, resolver(items).get)
        out += note_history(args, now, resolver(items).get, pages_now)
    out += brain.section(top, noted['items'])
    out += front_lines(notes, digest, by_id)
    today = dk(now).date().isoformat()
    for d in sorted(recent_days(moves, now), key=lambda d: d['date']):
        n = sum(len(tp['lines']) for tp in d['topics'])
        if d['date'] != today and dk(now).hour >= 10:   # yesterday is done: its topic names, to continue developments
            out += [f"## Yesterday's topics ({date_da(noon(datetime.fromisoformat(d['date'])))}, {n} lines) – continue one by "
                    'writing its name exactly as here', ''] + [f"- {tp['name']} ({tp['section']})" for tp in d['topics']] + ['']
            continue
        out += [f"## The recap of {date_da(noon(datetime.fromisoformat(d['date'])))} so far – {n} lines", '',
                f'Continue a topic by writing its name exactly as here. Lines, newest first ({RECAP_SHOWN} per topic): '
                '[id] Danish time · who: text', '']
        for tp in d['topics']:
            out.append(f"### {tp['name']} ({tp['section']})")
            out += [f"[{x['id']}] {dk(ts(x['at'])):%d.%m %H.%M} · {x['who'] + ': ' if x['who'] else ''}{x['text']}"
                    for x in tp['lines'][:RECAP_SHOWN]]
            if len(tp['lines']) > RECAP_SHOWN:
                out.append(f"(+{len(tp['lines']) - RECAP_SHOWN} earlier lines)")
            out.append('')
    out += ['## Top stories of the last 24 hours – for picks (strongest first)', '',
            'Fields: id · section · tier (the books\' order; 1 heaviest) · rank · outlets · title', '']
    for i in top:
        t = brain.tier_of(i)
        out.append(f"[{i['id']}] {i.get('sec')}{f' · tier {t}' if t is not None else ''} · rank {i.get('rank')} · "
                   f"{i.get('outlets', 1)} outlets · {i.get('title_tr') or i['title']}")
    out += ['', f'## Stories since {dk(start):%H.%M} {date_da(start)} – {len(news)}, strongest first – for recap lines', '',
            'Fields: id · section · tier · rank · big (many outlets) · outlets, by kind of media (+ those since the last '
            'update) · confirmed (established outlets; 0 = only Telegram/YouTube channels, so unconfirmed)', '']
    listed = set()
    for i, joined in news[:100]:
        out += story_lines(i, joined)
        listed.add(i['id'])
    owner = read(args, 'origin/data', 'removed.json', {'removed': [], 'moved': {}})
    gone = sorted(owner.get('removed') or [], key=lambda r: r['at'], reverse=True)[:OWNER_SHOWN]
    if gone:   # the owner's own verdicts from the app, stated plainly
        out += ['## What the owner removed from the app (newest first) – learn from it', '',
                'The owner held these down and removed them. Never pick, quote or recap stories like the irrelevant and not-news',
                'ones; let them tell you what he finds uninteresting. Duplicates only say the radar missed a match.', '']
        out += [f"- [{r['why']}] {r['title']} ({r['source']})" for r in gone] + ['']
    if owner.get('moved'):
        out += ['## Stories the owner moved to another section – the right place for stories like them', '']
        out += [f"- {i['title']} → {owner['moved'][i['id']]}" for i in items if i['id'] in owner['moved']] + ['']
    learned = read(args, 'origin/data', 'learned.json', [])
    opened = [x['id'] for x in learned if x.get('why') in ('read', 'copied') and x.get('at') and now - ts(x['at']) < timedelta(hours=24)]
    todo = to_summarise(items, set((summaries_of(args).get('items') or {})), now, opened)
    if todo:
        out += [f'## Stories to summarise – {len(todo)} (what readers see when they open a story; the ones readers opened first)', '',
                'You cannot open the articles (no internet here). For each, write 2-3 plain Danish sentences from what is given:',
                'the headline, the teaser under it and the other outlets\' headlines under "Also" – what happened, who, and why it',
                'matters, and nothing they do not support. No opinion, no reading, no "artiklen handler om". Set "paywall": true',
                '(the app then says the summary rests on the headlines and the outlets\' introductions).', '']
        for i in todo:
            out += [f"[{i['id']}] – listed above", ''] if i['id'] in listed else story_lines(i)
    app = app_of(args)
    live = read(args, 'origin/digest', 'live.json', {})
    pool, known = admitted(data, app, now, live)
    if not known:   # before the radar draws the line: the strongest stories of the day the app shows
        pool = [i for i in pool if in_24h(i, now)]
    heads = to_head(with_economy(pool, args, items), headlines_of(args), now, admitted_record(args))   # Økonomi's too (19/10)
    out += head_lines(heads, known, listed)
    level, the_plan = day_level(live, now), active_plan(live, now)
    out += live_lines(level, the_line(data, app), *around_the_line(data, pool, known, now, level, the_plan), pool, known,
                      now, the_plan)
    out += front_section(read(args, 'origin/digest', 'front.json', {}), resolver(items), notes, now)
    cal_now, kal_now = read(args, 'origin/data', 'calendar.json', {}), read(args, 'origin/digest', 'kalender.json', {})
    out += calendar_lines(cal_now, kal_now, now)
    heads_now = {k: (v.get('title') if isinstance(v, dict) else v) for k, v in (summaries_of(args).get('titles') or {}).items()}
    out += news_dates([*pool, *items], cal_now, kal_now, now, heads_now)
    evt_now = read(args, 'origin/digest', 'events.json', {'items': []})
    find_any = {**resolver([*pool, *items]), **wire_stories(lines)}.get
    out += event_pages.lines(evt_now, now, find_any, headline, teaser_of, development(moves, now),
                             read(args, 'origin/data', 'places.json', {}).get('places') or {})
    out += event_pages.great_lines(great_groups(pool, evt_now.get('items') or [], now), headline, teaser_of)
    out += [f'## Al Jazeera wire lines since the last update – {len(wire)}, oldest first', '',
            'Fields: [id] Danish date and time · Arabic original (machine English, only a hint)', '']
    for v in wire:
        out.append(f"[{v['i']}] {dk(ts(v['p'])):%d.%m %H.%M} · {v['t']}  ({v.get('tr') or '–'})")
    queue = waiting(args, noted)
    template = dict(TEMPLATE)
    if getattr(args, 'audit', False):
        template.update(CHIEF_TEMPLATE)
    if queue:
        out += [''] + answer_lines(queue[0], brain.known_ids() | used_ids(noted))
        template.update(ANSWER_TEMPLATE)
    out += [''] + SMALL + ['## Write /tmp/editor/update.json in exactly this shape (UTF-8 JSON)', '',
                           json.dumps(template, ensure_ascii=False, indent=1)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'input.md').write_text('\n'.join(out), encoding='utf-8')
    (WORK / 'input.meta').write_text(json.dumps({'digest': '' if args.dir else digest_head(), 'made': now.isoformat()}),
                                     encoding='utf-8')   # publish refuses when another update landed after this
    print(f'{WORK / "input.md"}: {len(top)} top stories, {len(news)} new stories since {dk(start):%H.%M}, '
          f"{len(wire)} wire lines{', a new answer to note' if queue else ''}")


# ------------------------------------------------------------------ publishing an update

def day_text(day):
    """The share text, in the format members post themselves ('Politiske nyheder')."""
    out = [day['title'], '']
    for tp in day['topics']:
        out += [tp['name'], '']
        for x in tp['lines']:
            out += [f"- {x['who']}: {x['text']}" if x['who'] else f"- {x['text']}", '']
    return '\n'.join(out).strip()


def push_text(day, now):
    """One notification a day, with the first update at or after 21 Danish time: the day's most important line, and
    how many more."""
    if dk(now).hour < EVENING or any(ts(u) < now and dk(ts(u)).hour >= EVENING and dk(ts(u)).date() == dk(now).date()
                                     for u in day.get('updates') or []):
        return None
    lines = [x for tp in day['topics'] for x in tp['lines']]
    if not lines:
        return None
    x = day['topics'][0]['lines'][0]
    return {'title': f"Khabar · dagens resumé, {dk(now).day}. {MONTHS[dk(now).month - 1]}",
            'body': (f"{x['who']}: {x['text']}" if x['who'] else x['text']) + (f'  (+{len(lines) - 1} mere)' if len(lines) > 1 else '')}


def live_day(draft, current, find, now, problems):
    """Today's Live as the editor sets it – level, take, drop, note – on top of what earlier updates set today; with
    the whole live.json (today and yesterday, Danish dates) to write. {'day': today's entry, 'file': live.json}."""
    stamp = now.isoformat(timespec='seconds')
    today = dk(now).date()
    wanted = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    days = {d: dict(v) for d, v in ((current or {}).get('days') or {}).items() if d in wanted and isinstance(v, dict)}
    day = days.get(today.isoformat(), {})
    changed = False
    if not kept(draft.get('level')):
        level = clean(draft.get('level')).casefold()
        if level not in LEVELS:
            problems.append(f"level: få, normal or mange – not {draft.get('level')!r} (or leave it out to keep today's)")
        else:
            day['level'], changed = level, True
    given = {}
    for f in ('take', 'drop'):
        v = draft.get(f)
        if kept(v):
            continue
        if not isinstance(v, list):
            problems.append(f'{f}: a list of story ids – or leave "{f}" out')
            continue
        given[f] = []
        for x in v:
            it = find.get(str(x))
            if not it:
                problems.append(f'{f}: unknown story id {x!r}')
            elif it['id'] not in given[f]:
                given[f].append(it['id'])
    both = set(given.get('take') or []) & set(given.get('drop') or [])
    if both:
        problems.append(f"take and drop: {', '.join(sorted(both))} – a story is taken in or out, not both")
    for f, other in (('take', 'drop'), ('drop', 'take')):
        for x in given.get(f) or []:
            day[other] = [y for y in day.get(other) or [] if find.get(y) is not find[x] and y != x]
            if not any(y == x or find.get(y) is find[x] for y in day.get(f) or []):
                day[f] = (day.get(f) or []) + [x]
            changed = True
    if not kept(draft.get('note')):
        note = clean(draft.get('note'))
        if len(note) > LIVE_NOTE:
            problems.append(f'note: one line (at most {LIVE_NOTE} characters, not {len(note)})')
        voice.check_voice(note, 'note', problems)
        voice.check_reality(note, 'note', problems)
        day['note'], changed = note, True
    if day:
        day = {'level': day.get('level') or 'normal', 'take': day.get('take') or [], 'drop': day.get('drop') or [],
               'note': day.get('note') or '', 'at': stamp if changed else day.get('at') or stamp}
        days[today.isoformat()] = day
    return {'day': day, 'file': {'updated': stamp, 'days': dict(sorted(days.items(), reverse=True))}}


DAY_MARK = re.compile(r'^\s*(?:i dag|i går|i morgen|i aften|i nat|i morges|i formiddag|i eftermiddag|mandag|tirsdag|onsdag|'
                      r'torsdag|fredag|lørdag|søndag)\b|\b\d{1,2}\.\s*(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)|'
                      r'\b\d{1,2}/\d{1,2}\b', re.I)


def refreshed(blocks, find):
    """A kept composition's blocks with their stories as the radar has them now: a story that left the radar is
    dropped, a block left empty with it."""
    out, used = [], set()

    def now_id(x):
        it = find.get(x)
        if it and it['id'] not in used:
            used.add(it['id'])
            return it['id']
        return None
    for b in blocks or []:
        b = dict(b)
        if b.get('kind') == 'top':
            b['story'] = now_id(b.get('story'))
            if not b['story']:
                continue
            b['with'] = [y for y in (now_id(x) for x in b.get('with') or []) if y]
        elif b.get('kind') == 'liste':
            b['stories'] = [y for y in (now_id(x) for x in b.get('stories') or []) if y]
            if not b['stories']:
                continue
        out.append(b)
    return out


def compose(spec, current, find, pool, topics, quotes, answers, lede, now, problems, lede_ids=None, events=None):
    """The front page as the editor composes it (front.json), or None when there is none to write. spec: the update's
    'front' – left out (or "keep"): the composition now stays, re-dated, its stories as the radar has them (not one of
    an earlier day after 06: the app's fixed page shows until a new one comes). pool: the ids in Live (None before the
    radar draws the line); topics: the recap's topic names; quotes: the front page's quotes after this update;
    answers: the answers' numbers a 'svar' may name (None: not checked)."""
    stamp = now.isoformat(timespec='seconds')
    if kept(spec) or (isinstance(spec, dict) and 'blocks' not in spec):
        cur = current or {}
        if not cur.get('blocks') or not cur.get('updated'):
            return None
        if dk(ts(cur['updated'])).date() < dk(now).date() and dk(now).hour >= QUIET_UNTIL:
            return None
        blocks = refreshed(cur['blocks'], find)
        if dk(ts(cur['updated'])).date() < dk(now).date():   # a line of yesterday ('… i dag') is not today's
            blocks = [b for b in blocks if b.get('kind') != 'linje']
        return {'updated': stamp, 'lede': lede, **({'lede_ids': lede_ids} if lede_ids else {}), 'blocks': blocks} if blocks else None
    if not isinstance(spec, dict) or not isinstance(spec.get('blocks'), list) or not spec['blocks']:
        problems.append('front: an object with "blocks" (a list of at least one block) – or leave "front" out to keep the '
                        'composition')
        return None
    blocks = spec['blocks']
    if len(blocks) > FRONT_BLOCKS:
        problems.append(f'front: {len(blocks)} blocks – at most {FRONT_BLOCKS}: overskuelighed før fuldstændighed')
    used, out, tops = {}, [], 0
    for k, b in enumerate(blocks, 1):      # every block is checked, so one round shows every problem
        if not isinstance(b, dict) or b.get('kind') not in FRONT_KINDS:
            kind = b.get('kind') if isinstance(b, dict) else b
            problems.append(f"front block {k}: kind {kind!r} – one of {', '.join(FRONT_KINDS)}")
            continue
        kind = b['kind']
        where = f'front block {k} ({kind})'
        row = {'kind': kind}

        def story(x, label):
            it = find.get(str(x)) if x else None
            if not it:
                problems.append(f'{where}: {label} – unknown story id {x!r}')
                return None
            if pool is not None and not ({it['id'], *(it.get('members') or [])} & pool) and not it.get('big'):
                problems.append(f'{where}: {label} {x} is not in Live today – take it in ("take") or choose another')
            if it['id'] in used:
                problems.append(f'{where}: {label} {x} is in {used[it["id"]]} already – a story in one block only')
            used[it['id']] = f'block {k}'
            return it['id']

        def topic(name):
            got = topics.get(key(name)) if name else None
            if not got:
                problems.append(f'{where}: {name!r} is no topic of the recap – write its name exactly as listed')
            return got

        def ids(v, label, most, least=0):
            if not isinstance(v, list) or not least <= len(v) <= most:
                problems.append(f'{where}: {label} – a list of {least}-{most} story ids' if least else
                                f'{where}: {label} – a list of at most {most} story ids')
                return []
            return [y for y in (story(x, label) for x in v) if y]

        title = clean(b.get('title'))
        if title and kind == 'top':
            if len(title) > TITLE_LEN:
                problems.append(f'{where}: title – one headline, at most {TITLE_LEN} characters')
            voice.check_headline(title, f'{where} title', problems)
        elif title and kind != 'linje':
            if len(title) > BLOCK_TITLE:
                problems.append(f'{where}: title – a short block title, at most {BLOCK_TITLE} characters')
            if DAY_MARK.search(title):
                problems.append(f"{where}: title {title!r} looks like a day marker – name what the block holds")
            voice.check_headline(title, f'{where} title', problems)
        if title and kind != 'linje':
            row['title'] = title
        if kind == 'top':
            tops += 1
            row['story'] = story(b.get('story'), 'story')
            if row['story'] and (find.get(row['story']) or {}).get('kind') == 'kommentar':
                problems.append(f"{where}: story {b.get('story')} is commentary (an opinion or analysis piece) – a main "
                                'story is news: put it in a list, or choose another')
            row['with'] = ids(b.get('with') or [], 'with', 3)
            if b.get('timeline'):
                row['timeline'] = topic(b['timeline'])
            row['picture'] = b.get('picture', True) is not False
        elif kind == 'liste':
            if not title:
                problems.append(f"{where}: needs a title (e.g. 'Danmark' or 'Krigen i Sudan')")
            row['stories'] = ids(b.get('stories'), 'stories', FRONT_LIST, 1)
            style = clean(b.get('style')) or 'kompakt'
            if style not in LIST_STYLES:
                problems.append(f"{where}: style kompakt or billeder, not {style!r}")
            row['style'] = style
        elif kind == 'udvikling':
            v = b.get('topics')
            if not isinstance(v, list) or not 1 <= len(v) <= FRONT_TOPICS:
                problems.append(f'{where}: topics – a list of 1-{FRONT_TOPICS} recap topic names')
                v = []
            row['topics'] = [t for t in (topic(x) for x in v) if t]
        elif kind == 'citat':
            ref = clean(b.get('quote')).casefold().lstrip('q')
            n = int(ref) if ref.isdigit() else 0
            if not 1 <= n <= len(quotes):
                problems.append(f"{where}: quote {b.get('quote')!r} – one of the front page's quotes, q1-q{len(quotes)}"
                                if quotes else f'{where}: there are no quotes – send "quotes" or leave the block out')
            else:
                q = quotes[n - 1]
                row.update({'quote': f'q{n}', 'who': q['who'], 'text': q['text'], 'link': q.get('link', ''),
                            'sec': q.get('sec')})
        elif kind == 'svar':
            nr = clean(b.get('nr'))
            if not nr or (answers is not None and nr not in answers):
                problems.append(f"{where}: nr {b.get('nr')!r} is no answer of Hizb ut-Tahrir's the app knows")
            row['nr'] = nr
        elif kind == 'live':
            n = b.get('n', 3)
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 10:
                problems.append(f'{where}: n – a number of stories, 1-10')
                n = 3
            row['n'] = n
        elif kind in ('begivenhed', 'tal', 'nedtaelling'):
            ev = (events or {}).get(clean(b.get('event')))
            if not ev:
                problems.append(f"{where}: event {b.get('event')!r} is no event page – write it under \"events\" first")
            else:
                row['event'] = ev['id']
                if kind == 'tal':
                    n = b.get('fact', 1)
                    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(ev.get('facts') or []):
                        problems.append(f"{where}: fact – the number of one of the page's fact boxes, 1-{len(ev.get('facts') or [])}"
                                        if ev.get('facts') else f'{where}: the event page has no fact boxes')
                    else:
                        row['fact'] = n
                if kind == 'nedtaelling' and ev.get('status') != 'kommende':
                    problems.append(f"{where}: a countdown is for an event ahead (status 'kommende')")
        elif kind == 'linje':
            text = clean(b.get('text'))
            if not text or len(text) > FRONT_LINE:
                problems.append(f'{where}: text – one short line of reality, at most {FRONT_LINE} characters')
            voice.check_headline(text, f'{where} text', problems)
            row['text'] = text
        out.append(row)
    if tops > FRONT_TOPS:
        problems.append(f"front: {tops} 'top' blocks – one, or two on a day with two main stories")
    return {'updated': stamp, 'lede': lede, **({'lede_ids': lede_ids} if lede_ids else {}), 'blocks': out}


def lede_links(draft, prev, lede, fresh, by_id, problems):
    """The story each part of the lede opens (`lede_ids`, one id per part of `lede_parts`, '' for a part that names
    none), or None: the app then finds them by the parts' words. Given with the lede (or with front.lede); a kept lede
    keeps its own. Each id is checked as the picks' are – a story of the pool, an old lead article's id resolved to its
    story's id now."""
    given = draft.get('lede_ids')
    if given is None and isinstance(draft.get('front'), dict):
        given = draft['front'].get('lede_ids')
    if kept(given):
        if fresh:
            return None   # a new lede without ids: the app matches its parts
        given, old = prev.get('lede_ids'), True
        if not isinstance(given, list):
            return None
    else:
        old = False
    if not isinstance(given, list):
        problems.append('lede_ids: a list of story ids, one per part of the lede in order ("" for none) – or leave it out')
        return None
    parts = lede_parts(lede)
    if not old and len(given) != len(parts):
        problems.append(f'lede_ids: {len(given)} ids for {len(parts)} parts of the lede – one per part, in order: '
                        + ' | '.join(f'{k}. {p}' for k, p in enumerate(parts, 1)))
    out = []
    for x in given[:len(parts)]:
        x = '' if x is None else str(x).strip()
        if not x:
            out.append('')
        elif x in by_id:
            out.append(by_id[x]['id'])
        elif old:
            out.append(x)   # its story left the radar: the app finds the part's story itself
        else:
            problems.append(f'lede_ids: unknown story id {x!r}')
    return out if any(out) else None


def build(draft, data, lines, moves, now, previous=None, extra=None):
    """The updated days and the editor's notes, or a list of problems to fix. A line goes into the day it happened
    (Danish date): after midnight what came before completes yesterday's recap. previous: the editor's notes on the
    front page now – the lede, picks and quotes an update leaves out stay, and moves stay until undone. extra: live.json
    and front.json as they are ('live', 'front'), the admitted stories when the radar draws the line ('pool') and the
    answers' numbers a 'svar' block may name ('answers')."""
    problems = []
    prev = previous or {}
    stamp = now.isoformat(timespec='seconds')
    today = dk(now).date()
    days = {d['date']: json.loads(json.dumps(d)) for d in recent_days(moves, now)}

    def day_for(at):
        date = max(dk(ts(at)).date(), today - timedelta(days=1))
        return days.setdefault(date.isoformat(), new_day(noon(date)))

    day_for(stamp)   # today exists, if only to keep the wire lines it was given
    by_id = {i['id']: i for i in data.get('items', [])}
    # a story may have changed its lead article since the input (the radar runs every five minutes): its old id is
    # one of its members now – find it by that, and file what the editor wrote under its current id
    for i in data.get('items', []):
        for m in i.get('members') or []:
            by_id.setdefault(m, i)
    by_line = {v['i']: v for v in lines.get('items', [])}
    wire = {v['i']: v for v in uncovered(lines, moves)}
    told = {x['id'] for d in days.values() for tp in d['topics'] for x in tp['lines'] if x.get('kind') == 's'}
    sections = {key(tp['name']): tp['section'] for d in days.values() for tp in d['topics']}
    used, picked, adds = {}, {}, []   # wire id -> where; story id -> where; (name, section, line)
    for k, tp in enumerate(draft.get('topics') or []):
        name = ' '.join(str(tp.get('name', '')).split())
        where = f"topic {k + 1} ({name or '?'})"
        if not name:
            problems.append(f'{where}: no name')
        section = sections.get(key(name)) or tp.get('section')
        if section not in SECTIONS:
            problems.append(f"{where}: section must be dk, me or world, not {tp.get('section')!r}")
        voice.check_voice(name, f'{where} name', problems)
        voice.check_reality(name, f'{where} name', problems)
        if not tp.get('lines'):
            problems.append(f'{where}: no lines')
        for line in tp.get('lines') or []:
            who, text = ' '.join(str(line.get('who', '')).split()), ' '.join(str(line.get('text', '')).split())
            ids, story = line.get('ids') or ([line['id']] if line.get('id') else []), line.get('story')
            label = f"{where}: the line '{who or '?'}: {text[:40]}…'"
            if not who or not text:
                problems.append(f'{label} needs who and text')
            elif len(text) > MAX_TEXT or len(who) > 80:
                problems.append(f'{label} is too long ({len(text)} characters) – one short sentence')
            voice.check_voice(f'{who}: {text}', label, problems)
            voice.check_distance(text, label, problems)
            voice.check_reality(text, label, problems)
            if not story and not ids:
                problems.append(f'{label} has neither a story id nor wire ids')
            it = None
            if story:
                it = by_id.get(story)
                if not it:
                    problems.append(f'{label}: unknown story id {story!r}')
                elif story in told or it['id'] in told:
                    problems.append(f'{label}: story {story} is in the recap already')
                elif story in picked:
                    problems.append(f'{label}: story {story} is used twice (also in {picked[story]})')
                picked[story] = where
            for i in ids:
                if i not in wire:
                    problems.append(f'{label}: {i!r} is no new wire line')
                elif i in used:
                    problems.append(f'{label}: wire line {i} is used twice (also in {used[i]})')
                used[i] = where
            first = wire.get(ids[0]) if ids else None
            if it and it.get('group') in MOVEMENT_GROUPS:   # the movement's or a government's own channel
                voice.check_movement(text, label, problems)
            if it:
                adds.append((name, section, {
                    'who': who, 'text': text, 'link': it['link'], 'source': it['source'],
                    'at': it.get('published') or it.get('found') or stamp, 'added': stamp, 'id': it['id'], 'kind': 's',
                    **({'confirmed': 0} if it.get('confirmed') == 0 else {})}))
            elif first:
                adds.append((name, section, {'who': who, 'text': text, 'link': first['u'], 'source': 'Al Jazeera',
                                             'at': first['p'], 'added': stamp, 'id': first['i'], 'kind': 'w'}))
    if len(adds) > MAX_NEW:
        problems.append(f'{len(adds)} lines – at most {MAX_NEW}: keep only the most important movements')
    names = set(sections) | {key(n) for n, _, _ in adds}
    order = [n for n in draft.get('order') or [] if str(n).strip()]
    problems += [f'order: {n!r} is no topic' for n in order if key(n) not in names]
    # the editor's notes for the app: the lede, stories that matter more, stories in the wrong section, statements
    if kept(draft.get('lede')):
        lede, lede_at = prev.get('lede') or '', prev.get('lede_at') or prev.get('created') or ''
        if not lede:
            problems.append('lede: there is no lede to keep – write one sentence of the day so far (at most about 25 words)')
        elif lede_at and dk(ts(lede_at)).date() < today and dk(now).hour >= QUIET_UNTIL:
            problems.append("lede: the lede on the front page is from an earlier day – write today's")
    else:
        lede, lede_at = ' '.join(str(draft.get('lede', '')).split()), stamp
        if not lede or len(lede) > 220:
            problems.append('lede: one sentence of the day so far is needed (at most about 25 words)')
        voice.check_voice(lede, 'lede', problems)
        voice.check_distance(lede, 'lede', problems)
        voice.check_reality(lede, 'lede', problems)
    picks, quotes = [], []
    if kept(draft.get('picks')):
        picks = [p for p in prev.get('picks') or [] if p.get('id') in by_id]
    elif not isinstance(draft.get('picks'), list):
        problems.append('picks: a list of stories – or leave "picks" out to keep the picks on the front page')
    else:
        for p in draft['picks'][:8]:
            if not isinstance(p, dict) or p.get('id') not in by_id:
                problems.append(f"picks: unknown story id {(p or {}).get('id') if isinstance(p, dict) else p!r}")
            else:
                why = ' '.join(str(p.get('why', '')).split())[:120]
                voice.check_voice(why, f"picks: {p['id']} why", problems)   # public in digest.json
                voice.check_reality(why, f"picks: {p['id']} why", problems)
                picks.append({'id': by_id[p['id']]['id'], 'why': why})
    fixes = {m['id']: m for m in prev.get('moves') or [] if isinstance(m, dict) and m.get('id') in by_id}
    for m in draft.get('moves') if isinstance(draft.get('moves'), list) else []:
        if not isinstance(m, dict) or m.get('id') not in by_id or m.get('sec') not in SECTIONS:
            problems.append(f'moves: {m!r} needs a known story id and a section dk, me or world')
        elif m['sec'] == by_id[m['id']].get('sec'):
            fixes.pop(m['id'], None)   # back where the radar put it: the move is undone
        else:
            fixes[m['id']] = {'id': m['id'], 'sec': m['sec']}
    if kept(draft.get('quotes')):
        quotes = list(prev.get('quotes') or [])
    elif not isinstance(draft.get('quotes'), list):
        problems.append('quotes: a list of statements – or leave "quotes" out to keep the quotes on the front page')
    else:
        for q in draft['quotes'][:8]:
            if not isinstance(q, dict):
                problems.append(f'quotes: {q!r} – an object with who, text, sec and ids or story')
                continue
            who, text = ' '.join(str(q.get('who', '')).split()), ' '.join(str(q.get('text', '')).split())
            src = by_id.get(q.get('story')) if q.get('story') else by_line.get((q.get('ids') or [None])[0])
            if not who or not text or len(text) > 300 or q.get('sec') not in SECTIONS or not src:
                problems.append(f"quotes: '{who}: {text[:40]}' needs who, a short text, a section and a known story or wire id")
            else:
                voice.check_voice(f'{who}: {text}', f"quotes: '{who}: {text[:40]}'", problems)
                if src.get('group') in MOVEMENT_GROUPS:
                    voice.check_movement(text, f"quotes: '{who}: {text[:40]}'", problems)
                # "okonomi": a statement on the economy – the economy page's 'Dagens citat' (the owner, 18/10)
                quotes.append({'who': who, 'text': text, 'sec': q['sec'], 'link': src.get('link') or src.get('u', ''),
                               **({'okonomi': True} if q.get('okonomi') is True else {})})
    find = resolver(data.get('items', []))
    # the news outlets only: a government's own channel ('Kreml', 'Det Hvide Hus') or the movement's is who speaks, and
    # 'Kreml: …' stays the attributed claim it is
    outlet_labels = {str(v.get('label') or k).casefold() for k, v in (data.get('sources') or {}).items()
                     if (v.get('group') or 'west') in voice.NEWS_GROUPS}
    heads = []
    for x in (draft.get('titles') or [])[:MAX_TITLES + 10]:
        x = x if isinstance(x, dict) else {'id': x}
        title = ' '.join(str(x.get('title', '')).split())
        it = find.get(x.get('id'))
        if not it:
            problems.append(f"titles: unknown story id {x.get('id')!r}")
        elif not title or len(title) > TITLE_LEN:
            problems.append(f"titles: {x['id']} needs one Danish headline (at most {TITLE_LEN} characters, not {len(title)})")
        else:
            voice.check_headline(title, f"titles: {x['id']}", problems)
            voice.check_prefix(title, [it.get('source'), *(a.get('source') for a in it.get('also') or [])], outlet_labels,
                               f"titles: {x['id']}", problems)
            if it.get('group') in MOVEMENT_GROUPS:
                voice.check_movement(title, f"titles: {x['id']}", problems)
            heads.append({'id': it['id'], 'title': title, 'members': sorted(set(it.get('members') or []) - {it['id']})})
    if len(draft.get('titles') or []) > MAX_TITLES + 10:
        problems.append(f"titles: {len(draft['titles'])} – at most {MAX_TITLES} (the ones the input lists)")
    sums = []
    for x in (draft.get('summaries') or [])[:MAX_SUM + 5]:
        text = ' '.join(str(x.get('text', '')).split())
        if x.get('id') not in by_id:
            problems.append(f"summaries: unknown story id {x.get('id')!r}")
        elif not text or len(text) > SUM_LEN:
            problems.append(f"summaries: {x['id']} needs 2-3 sentences (at most {SUM_LEN} characters, not {len(text)})")
        elif not isinstance(x.get('paywall', False), bool):
            problems.append(f"summaries: {x['id']} paywall must be true or false")
        else:
            voice.check_voice(text, f"summaries: {x['id']}", problems)
            voice.check_distance(text, f"summaries: {x['id']}", problems)
            voice.check_reality(text, f"summaries: {x['id']}", problems)
            sums.append({'id': by_id[x['id']]['id'], 'text': text, 'paywall': bool(x.get('paywall'))})
    quotes = [{**q, 'id': f'q{k}'} for k, q in enumerate(quotes, 1)]   # a front page's 'citat' names one by its id
    extra = extra or {}
    live = live_day(draft, extra.get('live'), find, now, problems)
    topics = {key(tp['name']): tp['name'] for d in moves.get('days') or [] for tp in d.get('topics') or []}
    topics.update({key(tp['name']): tp['name'] for d in days.values() for tp in d['topics']})
    topics.update({key(n): n for n, _, _ in adds})
    pool = extra.get('pool')
    if pool is not None:   # the radar draws the line: a front page's stories are in Live, or taken in today
        pool = {i['id'] for i in pool} | {m for i in pool for m in i.get('members') or []} | set(live['day'].get('take') or [])
    front_lede = (draft.get('front') or {}).get('lede') if isinstance(draft.get('front'), dict) else None
    if front_lede is not None and not kept(front_lede) and str(front_lede).strip():
        front_lede = ' '.join(str(front_lede).split())
        if not kept(draft.get('lede')) and front_lede != lede:
            problems.append('front: lede – give the lede once (in "lede" or in "front"), not two different ones')
        elif kept(draft.get('lede')):
            lede, lede_at = front_lede, stamp
            if len(lede) > 220:
                problems.append('front: lede – one sentence of the day so far (at most about 25 words)')
            voice.check_voice(lede, 'front: lede', problems)
            voice.check_reality(lede, 'front: lede', problems)
            problems[:] = [p for p in problems if not p.startswith('lede: ')]   # the front page's lede is the update's
    lede_ids = lede_links(draft, prev, lede, lede_at == stamp, by_id, problems)
    front = compose(draft.get('front'), extra.get('front'), find, pool, topics, quotes, extra.get('answers'), lede, now,
                    problems, lede_ids, extra.get('events'))
    if front and lede and lede_at == stamp:   # a new lede is a standfirst: it does not repeat the main story's headline
        top = next((b for b in front['blocks'] if b.get('kind') == 'top'), None)
        if top:
            voice.check_lede(lede, top.get('title') or headline(find.get(top.get('story')) or {}), 'lede', problems)
    if problems:
        return None, None, problems
    touched = set()
    for name, section, line in adds:
        d = day_for(line['at'])
        topic_of(d, name, section)['lines'].append(line)
        touched.add(d['date'])
    rank = {key(n): j for j, n in enumerate(order)}
    for d in days.values():
        for tp in d['topics']:
            newest_first(tp)
        d['topics'] = sorted((tp for tp in d['topics'] if tp['lines']), key=lambda tp: rank.get(key(tp['name']), len(rank)))
    now_day = days[today.isoformat()]
    now_day['ids'] = sorted(set(now_day['ids']) | set(wire))   # every line it was given, used or not, is done
    for date in touched | {today.isoformat()}:
        days[date]['updates'] = days[date]['updates'] + [stamp]
        days[date]['created'] = stamp
    notes = {'created': stamp, 'lede': lede, 'lede_at': lede_at, **({'lede_ids': lede_ids} if lede_ids else {}),
             'picks': picks, 'moves': list(fixes.values()), 'quotes': quotes, 'summaries': sums, 'titles': heads,
             'live': live, 'front': front}
    return days, notes, []


# ------------------------------------------------------------------ Hizb ut-Tahrir's new answer

def used_ids(noted):
    """The subject ids the answers noted so far use."""
    return {x for a in (noted.get('items') or {}).values() for r in a.get('readings') or []
            for x in (r.get('subject'), r.get('object')) if x} | \
           {b for a in (noted.get('items') or {}).values() for b in a.get('begreber') or []}


def id_problem(sid, known):
    """None when the id is a known subject or concept, or a well-formed new one; else what is wrong."""
    if not sid:
        return 'is missing'
    if sid in known:
        return None
    if not SUBJECT_ID.match(sid):
        return f'{sid!r}: a known id or a new lowercase-with-hyphens id (a relation: a--b)'
    if '--' in sid and sid != '--'.join(sorted(sid.split('--'))):
        return f"{sid!r}: a relation's two ids in alphabetical order, {'--'.join(sorted(sid.split('--')))!r}"
    flat = re.sub(r'[^a-z0-9]', '', sid)
    twin = next((k for k in sorted(known) if re.sub(r'[^a-z0-9]', '', k) == flat), None)
    return f'{sid!r}: use the known id {twin!r}' if twin else None


def check_answer(obj, queue, known):
    """The update's 'answer': Hizb ut-Tahrir's new answer as the shared schema's answers.json item, or the problems.
    Everything in it is the movement's reading, said in plain Danish without its attribution – the app shows note_da and
    every reading under the label 'Hizb ut-Tahrirs svar · d/m/åååå' (voice.check_plain) – and the content rules hold
    (voice.py)."""
    if not isinstance(obj, dict):
        return None, ['answer: one object in the shape shown – or leave "answer" out']
    nr = str(obj.get('nr') or '').strip()
    src = queue.get(nr)
    if not src:
        return None, [f"answer: {nr or '?'} is no new answer of Hizb ut-Tahrir in the input – note the one the input shows"]
    problems, where = [], f'answer {nr}'
    date = str(src.get('date') or '')[:10]
    if str(obj.get('date') or date)[:10] != date:
        problems.append(f"{where}: date must be the answer's own, {date}")
    title, question, note = (clean(obj.get(f)) for f in ('title_da', 'question_da', 'note_da'))
    if not title or len(title) > 200:
        problems.append(f'{where}: title_da – the title in Danish, at most 200 characters')
    if not question or len(question) > 600:
        problems.append(f'{where}: question_da – the question in one or two Danish sentences, at most 600 characters')
    if not note or len(note) > NOTE_LEN:
        problems.append(f'{where}: note_da – 2-4 Danish sentences, at most {NOTE_LEN} characters')
    else:
        voice.check_plain(note, f'{where} note_da', problems)
    rows = obj.get('readings') or []
    if not isinstance(rows, list):
        problems.append(f'{where}: readings – a list')
        rows = []
    if len(rows) > MAX_READINGS:
        problems.append(f'{where}: {len(rows)} readings – at most {MAX_READINGS}: the subjects it reads most')
    readings = []
    for k, r in enumerate(rows[:MAX_READINGS], 1):
        at = f'{where} reading {k}'
        if not isinstance(r, dict):
            problems.append(f'{at}: an object with subject, kind and text_da')
            continue
        subject, kind, text = str(r.get('subject') or '').strip(), str(r.get('kind') or '').strip(), clean(r.get('text_da'))
        bad = id_problem(subject, known)
        if bad:
            problems.append(f'{at}: subject {bad}')
        if kind not in ANSWER_KINDS:
            problems.append(f"{at}: kind must be one of {', '.join(ANSWER_KINDS)}")
        if not text or len(text) > READING_LEN:
            problems.append(f'{at}: text_da – one sentence, at most {READING_LEN} characters')
        else:
            voice.check_plain(text, f'{at} text_da', problems)
        row = {'subject': subject, 'kind': kind}
        if r.get('object'):
            other = str(r['object']).strip()
            bad = id_problem(other, known)
            if bad:
                problems.append(f'{at}: object {bad}')
            row['object'] = other
        if r.get('value'):
            row['value'] = clean(r['value'])
            if len(row['value']) > 60:
                problems.append(f'{at}: value – a short label (at most 60 characters)')
        row['text_da'] = text
        readings.append(row)
    begreber = []
    for b in obj.get('begreber') or []:
        b = str(b).strip()
        bad = id_problem(b, known)
        if bad:
            problems.append(f'{where}: begreber {bad}')
        elif b not in begreber:
            begreber.append(b)
    for label, text in [('title_da', title), ('question_da', question), ('note_da', note)] + \
                       [(f"reading {k} ({r['subject']})", r['text_da']) for k, r in enumerate(readings, 1)]:
        voice.check_voice(text, f'{where} {label}', problems)
        voice.check_movement(text, f'{where} {label}', problems)
    if problems:
        return None, problems
    return {'nr': nr, 'date': date, 'title_da': title, 'question_da': question, 'note_da': note,
            'url': src.get('url') or clean(obj.get('url')), 'readings': readings, 'begreber': begreber}, []


# ------------------------------------------------------------------ the calendar's planned events from the news

CAL_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CAL_MONTH = re.compile(r'^\d{4}-\d{2}$')


def cal_last_day(e):
    """The last day an entry lasts (a month only: its last day), as a date; None when it cannot be read."""
    d = str(e.get('end') or e.get('date') or '')
    try:
        if re.fullmatch(r'\d{4}', d):   # a year alone (the radar's annual meetings and undated elections): 31 December
            return datetime(int(d), 12, 31).date()
        if CAL_MONTH.match(d):
            y, m = int(d[:4]), int(d[5:7])
            return datetime(y + m // 12, m % 12 + 1, 1).date() - timedelta(days=1)
        return datetime.fromisoformat(d).date()
    except ValueError:
        return None


def cal_slug(text):
    t = str(text or '').lower().translate(str.maketrans({'æ': 'ae', 'ø': 'oe', 'å': 'aa', '“': '', '”': ''}))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:40].strip('-')


def cal_words(title):
    t = str(title or '').lower().translate(str.maketrans({'“': ' ', '”': ' '}))
    return {w for w in re.split(r'[^\w]+', t) if len(w) >= 4}


def cal_same(a, b):
    """Two calendar entries for one event: the same day, and the same source or nearly the same title (four fifths of
    the shorter title's words in the other) – 'Libanon deltager i … samtaler med “israel”' and the same '… i Florida'."""
    if str(a.get('date')) != str(b.get('date')):
        return False
    if a.get('link') and a.get('link') == b.get('link'):
        return True
    x, y = cal_words(a.get('title')), cal_words(b.get('title'))
    return bool(x and y) and len(x & y) >= 0.8 * min(len(x), len(y))


def calendar_file(entries, current, find, now, problems):
    """kalender.json as this update leaves it: the earlier entries still ahead (or at most CAL_KEEP days past), with the
    update's own added, changed (the same id) or removed ({"id": …, "remove": true}). An entry is a planned event the news
    name – date (YYYY-MM-DD, or YYYY-MM with "approx": true), title, kind, why (one factual line on why it matters, never
    a forecast), link and ids (the stories it comes from); every word of it is checked like a headline."""
    today = dk(now).date()
    stamp = now.isoformat(timespec='seconds')
    items = {e['id']: e for e in (current or {}).get('items') or [] if isinstance(e, dict) and e.get('id')}
    # what the file holds twice already (two updates, one event) is one entry again: the newest stays
    for e in sorted(items.values(), key=lambda e: str(e.get('at') or ''), reverse=True):
        if e['id'] in items:
            for other in [o for o in items.values() if o['id'] != e['id'] and cal_same(o, e)]:
                items.pop(other['id'])
    if entries is not None and not isinstance(entries, list):
        problems.append('calendar: a list of planned events – or leave "calendar" out to keep the calendar as it is')
        entries = []
    entries = entries or []
    if len(entries) > CAL_MAX:
        problems.append(f'calendar: {len(entries)} entries – at most {CAL_MAX} in one update')
    for k, x in enumerate(entries[:CAL_MAX], 1):
        where = f'calendar {k}'
        if not isinstance(x, dict):
            problems.append(f'{where}: an object with date, title, kind, why, link and ids')
            continue
        if x.get('remove'):
            if x.get('id') not in items:
                problems.append(f"{where}: {x.get('id')!r} is no entry of the calendar to remove")
            else:
                items.pop(x['id'])
            continue
        date, approx = str(x.get('date') or '').strip(), bool(x.get('approx'))
        title, why = clean(x.get('title')), clean(x.get('why'))
        kind, place, link = str(x.get('kind') or '').strip(), clean(x.get('place')), str(x.get('link') or '').strip()
        where = f"{where} ({title[:40] or '?'})"
        last = cal_last_day({'date': date, 'end': x.get('end')})
        if not (CAL_DATE.match(date) or (CAL_MONTH.match(date) and approx)) or last is None:
            problems.append(f"{where}: date must be YYYY-MM-DD, or YYYY-MM with \"approx\": true – not {date or '?'!r}")
        elif last < today:
            problems.append(f'{where}: {date} has passed – the calendar holds what is ahead')
        end = str(x.get('end') or '').strip()
        if end and (not CAL_DATE.match(end) or end < date):
            problems.append(f'{where}: end must be YYYY-MM-DD on or after the date')
        if not title or len(title) > CAL_TITLE:
            problems.append(f'{where}: title – what happens, in Danish (at most {CAL_TITLE} characters)')
        else:
            voice.check_headline(title, f'{where} title', problems)
            voice.check_forecast(title, f'{where} title', problems)
        if kind not in CAL_KINDS:
            problems.append(f"{where}: kind must be one of {' | '.join(CAL_KINDS)}")
        if not why or len(why) > CAL_WHY:
            problems.append(f'{where}: why – one factual line on why it matters (at most {CAL_WHY} characters)')
        else:
            voice.check_voice(why, f'{where} why', problems)
            voice.check_reality(why, f'{where} why', problems)
            voice.check_forecast(why, f'{where} why', problems)
        if place:
            voice.check_voice(place, f'{where} place', problems)
        if link and not re.match(r'^https?://\S+$', link):
            problems.append(f'{where}: link must be the source\'s address (http…)')
        ids, stories = [], []
        for sid in x.get('ids') or []:
            it = find.get(sid)
            if not it:
                problems.append(f'{where}: unknown story id {sid!r}')
            else:
                ids.append(it['id'])
                stories.append(it)
        if not ids and not link:
            problems.append(f'{where}: name the stories it comes from (ids) or its source (link)')
        ident = str(x.get('id') or '').strip() or f'ed-{date}-{cal_slug(title)}'
        if not re.match(r'^[a-z0-9][a-z0-9-]{2,80}$', ident):
            problems.append(f'{where}: id must be lowercase letters, digits and hyphens')
        w = x.get('weight', x.get('w'))   # 3 high, 2 middle, 1 the rest (the owner, 17/10); left out: the app's 1
        if w is not None and w not in (1, 2, 3):
            problems.append(f'{where}: weight is 1, 2 or 3 (3 the events that move the balance of the powers)')
        item = {'id': ident, 'date': date, **({'end': end} if end else {}), **({'approx': True} if approx else {}),
                **({'w': w} if w in (1, 2, 3) else {}),
                'title': title, 'kind': kind, **({'place': place} if place else {}), 'why': why,
                'link': link or (stories[0].get('link') if stories else ''), **({'ids': ids} if ids else {}),
                'at': stamp, 'src': 'ed'}
        # one event once (the owner, 18/10: 'Libanon historien i kalender vises dobbelt?' – two updates named the same
        # talks under two ids): an entry on the same day with the same source or nearly the same title is the same
        # event, and this update's version replaces it
        for other in [e for e in items.values() if e['id'] != ident and cal_same(e, item)]:
            items.pop(other['id'])
        items[ident] = item
    keep = [e for e in items.values() if (cal_last_day(e) or today) >= today - timedelta(days=CAL_KEEP)]
    keep.sort(key=lambda e: (str(e.get('date')), e['id']))
    return {'updated': stamp, 'items': keep}


def calendar_lines(cal, kal, now):
    """The input's view of the calendar: what the next CAL_AHEAD days hold, the radar's and the editor's, so an update
    adds only what the news name and the calendar lacks."""
    today = dk(now).date()
    until = today + timedelta(days=CAL_AHEAD)
    ed = [e for e in (kal or {}).get('items') or [] if isinstance(e, dict)]
    src = [e for e in (cal or {}).get('items') or [] if isinstance(e, dict)]
    rows = []
    for e, who in [(e, 'editor') for e in ed] + [(e, 'radar') for e in src]:
        last = cal_last_day(e)
        if last is None or last < today or str(e.get('date'))[:10] > until.isoformat():
            continue
        rows.append((str(e.get('date')), who, e))
    rows.sort(key=lambda r: (r[0], r[1]))
    out = [f'## The calendar – the next {CAL_AHEAD} days ({len(rows)} planned events)', '',
           'The Kalender tab shows these. Add with "calendar" the planned events the news name and the calendar lacks (a',
           "ceasefire's end, talks, a Security Council vote, a court's ruling, a deadline, a Danish vote); change one of yours",
           'by giving its id, remove one with {"id": …, "remove": true}. Fields: [id] date · kind · title (place) – whose', '']
    out += [f"[{e.get('id')}] {d}{' (forventet)' if e.get('approx') else ''} · {e.get('kind')} · {e.get('title')}"
            f"{' (' + e['place'] + ')' if e.get('place') else ''} – {who}" for d, who, e in rows] or ['(nothing planned)']
    return out + ['']


# ------------------------------------------------------------------ dates in the news (the owner, 18/10: the calendar
# looked empty and the editor had added nothing – a ceasefire's end, a truce's expiry, a vote the news named): the
# stories of the last two days whose headline, teaser or other outlets name a coming day or a deadline, each with what
# the calendar holds on that day, so the editor decides on every one
NEWS_DATES_MAX = 15
MONTHS_DA = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december']
MONTHS_EN = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
_MON = '|'.join(MONTHS_DA + MONTHS_EN + [m[:3] for m in MONTHS_EN if len(m) > 3])
DAY_MONTH = re.compile(rf'\b(\d{{1,2}})\.?\s+({_MON})\b\.?|\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b', re.I)
# a deadline's own words name a coming event without a day; the weaker ones (a summit, a hearing) count only with one
DEADLINE = re.compile(r'\b(?:frist(?:en)?|udløber|ultimatum|deadline|expire[sd]?|expiry|våbenhvile[n]? (?:slutter|udløber)|'
                      r'ceasefire (?:ends|expires)|truce (?:ends|expires)|stemmer om|afstemning(?:en)? om|votes? on|'
                      r'(?:will|to) vote|folkeafstemning|dom (?:ventes|afsiges)|ruling (?:due|expected)|'
                      r'inden for \d+ (?:dage|timer)|within \d+ (?:days|hours)|senest (?:den|på)|no later than)\b', re.I)
EVENTISH = re.compile(r'\b(?:høring(?:en)?|hearing|topmøde(?:t)?|summit|møde(?:t)?|meeting|talks|forhandling(?:er)?|'
                      r'referendum|valg(?:et)?|election|retssag|trial|afstemning|truce|våbenhvile(?:n)?|ceasefire|'
                      r'aftale(?:n)?|deal|agreement|sanktion(?:er)?|sanctions?|told(?:en)?|tariffs?)\b', re.I)


def date_in(text, today):
    """The first coming day a text names ('12. november', 'November 12', 'Jan 10'): a date, or None; a day already
    passed this year is next year's."""
    for m in DAY_MONTH.finditer(text or ''):
        day, mon = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        name = mon.lower().rstrip('.')
        k = next((n for n, full in enumerate(MONTHS_EN) if full.startswith(name) and len(name) >= 3), None)
        k = MONTHS_DA.index(name) if name in MONTHS_DA else k
        if k is None:
            continue
        try:
            d = datetime(today.year, k + 1, int(day)).date()
        except ValueError:
            continue
        if d < today:
            if today - d < timedelta(days=120):
                continue   # a day just passed ('the October 5 attack') is no coming event
            d = d.replace(year=today.year + 1)   # 'January 10' said in October is next year's
        if d - today <= timedelta(days=400):
            return d
    return None


def news_dates(stories, cal, kal, now, titles=None):
    """Lines for the input: stories naming a coming day or a deadline, the day if one is named, and what the calendar
    holds then ('kalenderen har: …' or 'ikke i kalenderen')."""
    today = dk(now).date()
    entries = [e for e in ((kal or {}).get('items') or []) + ((cal or {}).get('items') or []) if isinstance(e, dict)]
    rows, seen = [], set()
    for i in stories:
        if i['id'] in seen or not in_48h(i, now):
            continue
        texts = [(titles or {}).get(i['id']) or '', i.get('title_tr') or i.get('title') or '', i.get('summary_tr') or i.get('summary') or '',
                 *[a.get('title_tr') or a.get('title') or '' for a in (i.get('also') or [])[:6]]]
        text = ' · '.join(t for t in texts if t)
        d = date_in(text, today)
        if d == today:
            d = None   # today's day is mostly the story's own dateline
        cue = DEADLINE.search(text) or (EVENTISH.search(text) if d else None)
        if not cue:
            continue   # a day without a deadline's or an event's word is a figure or a dateline
        seen.add(i['id'])
        held = [e for e in entries if d and str(e.get('date'))[:10] in (d.isoformat(), d.isoformat()[:7])]
        what = (f"{d:%d.%m.%Y} · " if d else '') + (f"«{cue.group(0)}» · " if cue else '')
        has = ('kalenderen har: ' + '; '.join(str(e.get('title')) for e in held[:2])) if held else ('ikke i kalenderen' if d else 'ingen dato nævnt')
        rows.append((0 if d and not held else 1 if d else 2, -(i.get('rank') or 0),
                     f"[{i['id']}] {what}{(titles or {}).get(i['id']) or i.get('title_tr') or i['title']} – {has}"))
    rows.sort()
    if not rows:
        return []
    return [f'## Dates in the news – {min(len(rows), NEWS_DATES_MAX)} stories of the last two days that name a coming day or a deadline',
            '', 'Decide on every line: a planned event of weight the calendar lacks goes into "calendar" (its date, a title that',
            'says what happens, kind, place, a factual why, the story ids); a line that is no planned event (a day already',
            'passed, an anniversary, a figure) is skipped without a word. The first lines name a day the calendar lacks.', '',
            *[r[2] for r in rows[:NEWS_DATES_MAX]], '']


def digest_head():
    """The digest branch's commit as this checkout knows it ('' when there is none)."""
    try:
        return subprocess.run(['git', 'rev-parse', '--verify', '-q', 'origin/digest'], capture_output=True,
                              check=True).stdout.decode().strip()
    except (subprocess.CalledProcessError, OSError):
        return ''


# fields that hold ids, links, times or codes – never Danish text – are left as they are by quoted()
NOT_TEXT = {'id', 'ids', 'story', 'stories', 'nr', 'with', 'quote', 'members', 'take', 'drop', 'lede_ids', 'link', 'url',
            'u', 'source', 'sec', 'section', 'date', 'at', 'added', 'created', 'updated', 'lede_at', 'kind', 'style',
            'level', 'picture', 'period', 'subjects', 'begreber', 'cites', 'n'}


def quoted(x, key=None):
    """Every Danish text in a file the editor writes, with the name Israel in the owner's house style (voice.quote_israel):
    the draft before it is checked, the stored files before they are merged, so a topic named before keeps its name."""
    if key in NOT_TEXT:
        return x
    if isinstance(x, str):
        return voice.quote_israel(x)
    if isinstance(x, list):
        return [quoted(v, key) for v in x]
    if isinstance(x, dict):
        return {k: quoted(v, k) for k, v in x.items()}
    return x


def cmd_publish(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    draft = quoted(json.loads(Path(args.file).read_text(encoding='utf-8')))
    if args.push and not args.dir:   # four routines an hour: another update may have landed since this input
        subprocess.run(['git', 'fetch', '-q', 'origin', '+refs/heads/digest:refs/remotes/origin/digest'], capture_output=True)
        try:
            base = json.loads((WORK / 'input.meta').read_text(encoding='utf-8')).get('digest')
        except (OSError, ValueError):
            base = None
        if base and digest_head() and base != digest_head():
            print('Not published – another update was published after your input was made (the digest branch moved): '
                  'run `python3 scripts/editor.py input` again and write the update on top of the new front page.')
            sys.exit(1)
    data, lines, moves = material(args)
    moves = quoted(moves)
    current = quoted(read(args, 'origin/digest', 'digest.json', {}))
    noted = answers_of(args)
    live_now = read(args, 'origin/digest', 'live.json', {})
    pool, known = admitted(data, app_of(args), now, live_now)
    fetched = read(args, 'origin/data', 'analyses.json', {'items': []})
    fetched = fetched.get('items') if isinstance(fetched, dict) else fetched
    extra = {'live': live_now, 'front': quoted(read(args, 'origin/digest', 'front.json', {})),
             'pool': pool if known else None,
             'answers': {str(k) for k in brain.static_answers()} | {str(k) for k in noted.get('items') or {}}
             | {str(a.get('id')) for a in fetched or [] if isinstance(a, dict) and a.get('id')}}
    ev_problems = []
    evt = event_pages.events_file(draft.get('events'), quoted(read(args, 'origin/digest', 'events.json', {'items': []})),
                                  {**resolver(data.get('items', [])), **wire_stories(lines)}, now, dk(now).date(), ev_problems, voice,
                                  event_pictures(owner_state(args), data.get('items', [])))
    extra['events'] = {e['id']: e for e in evt['items']}
    days, notes, problems = build(draft, data, lines, moves, now, current.get('editor') or {}, extra)
    problems += ev_problems
    # the page and its own development agree (18/10: the boxes said 150 police injured, 'Forløbet' under them 997): a
    # count this update puts in a page's development, or a page this update changes, leaves no box behind it
    touched = {str(e.get('id')) for e in draft.get('events') or [] if isinstance(e, dict)}
    after = {'days': [*(days or {}).values(), *[d for d in moves.get('days') or [] if d['date'] not in (days or {})]]}
    for page, gaps in behind_pages(evt['items'], after, now) if days else []:
        mine = [g for g in gaps if g[3].get('added') == notes['created']]
        for what, have, n, line, where in (gaps if page['id'] in touched else mine):
            fix = ("put the count in the page's box (cite the line's id – a wire line grounds a box too; the old value as "
                   "\"was\" only when the same giver gave it)" if where == 'boksen' else
                   "tell the newest count in the article, with who gives it (cite the line's id); an earlier count stays only "
                   "as the earlier one")
            problems.append(f"events {page['id']}: its development counts {n} {what} (line [{line.get('id')}]: "
                            f"{clip(line.get('text'), 90)}) – {'the box says' if where == 'boksen' else 'the article tells at most'} "
                            f"{have if have is not None else 'nothing'}; {fix}, or the page contradicts itself")
    answer = None
    if draft.get('answer'):
        answer, more = check_answer(draft['answer'], {str(a['id']): a for a in waiting(args, noted)},
                                    brain.known_ids() | used_ids(noted))
        problems += more
    kal = calendar_file(draft.get('calendar'), quoted(read(args, 'origin/digest', 'kalender.json', {'items': []})),
                        resolver(data.get('items', [])), now, problems)
    memo = memo_file(draft.get('memo'), read(args, 'origin/digest', 'memo.json', {}), now, problems)
    lessons = lessons_file(draft.get('lessons'), read(args, 'origin/digest', 'lessons.json', {}), now, problems)
    report = report_file(draft.get('report'), now, problems)
    answered = owner_file(draft.get('owner_notes'), read(args, 'origin/digest', 'owner.json', {}),
                          owner_state(args).get('notes') or [], now, problems)
    oko = econ.okonomi_file(draft.get('okonomi'), read(args, 'origin/digest', 'okonomi.json', {}), resolver(data.get('items', [])).get,
                            read(args, 'origin/data', 'calendar.json', {}), kal, now, problems, voice, titled_by(args, draft))
    if problems:
        print('Not published – fix these in the file and run publish again:')
        print('\n'.join('- ' + p for p in problems))
        sys.exit(1)
    merged = {d['date']: d for d in moves.get('days') or []}
    merged.update(days)
    archive = sorted(merged.values(), key=lambda d: d['date'], reverse=True)[:KEEP]
    today = days[dk(now).date().isoformat()]
    shown = today if today['topics'] else next((d for d in archive if d['topics']), today)   # early morning: yesterday
    sums, heads, before = notes.pop('summaries'), notes.pop('titles'), summaries_of(args)
    live, front = notes.pop('live'), notes.pop('front')
    recent = lambda d: {k: v for k, v in (d or {}).items() if now - ts(v['at']) < timedelta(days=SUM_DAYS)}  # noqa: E731
    kept_sums, checked = recent(before.get('items')), recent(before.get('titles'))
    # a stored headline that breaks today's rules (an earlier round's question or op-ed thesis) is dropped: the story
    # comes back under 'Headlines to write'
    dropped_titles = [k for k, v in checked.items() if not good_title((v or {}).get('title'))]
    for k in dropped_titles:
        checked.pop(k)
    kept_sums.update({x['id']: {'text': x['text'], 'paywall': x['paywall'], 'at': notes['created']} for x in sums})
    for x in heads:   # filed under the card's id, with its other articles: the card's lead may change
        for k in [k for k, v in checked.items() if k in x['members'] or x['id'] in ((v or {}).get('members') or [])]:
            checked.pop(k)   # the same story's earlier headline under another lead
        checked[x['id']] = {'title': x['title'], 'at': notes['created'], **({'members': x['members']} if x['members'] else {})}
    if answer:
        noted['items'][answer['nr']] = answer
    digest = {**shown, 'period': period_of(now), 'whatsapp': day_text(shown), 'push': push_text(shown, now), 'editor': notes}
    files = {'digest.json': digest, 'moves.json': {'updated': notes['created'], 'days': archive},
             'summaries.json': {'updated': notes['created'], 'items': kept_sums, 'titles': checked},
             'answers.json': {'items': dict(sorted(noted['items'].items(), key=lambda kv: str(kv[1].get('date') or ''),
                                                   reverse=True))},
             'live.json': live['file'], 'kalender.json': kal, 'events.json': evt}
    if front:
        files['front.json'] = front
    if memo:
        files['memo.json'] = memo
    if lessons:
        files['lessons.json'] = lessons
    if report:
        files['report.json'] = report
    if oko:
        files['okonomi.json'] = oko
    if answered:
        files['owner.json'] = answered
    files['runs.json'] = runs_file(read(args, 'origin/digest', 'runs.json', {}), runner(draft, now), run_note(draft), now)
    out = Path(args.out) if args.out else WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    for name in DIGEST_FILES:   # a file of an earlier publish this update does not write is never pushed again
        if name not in files and (out / name).exists():
            (out / name).unlink()
    for name, obj in files.items():
        (out / name).write_text(json.dumps(quoted(obj), ensure_ascii=False, indent=1), encoding='utf-8')
    pics = {}
    shutil.rmtree(out / ARCHIVE, ignore_errors=True)   # only this update's day goes into the archive
    if front:   # the day's front page, over the one the day's earlier update left: the last update of the day stays
        mine = {k: v for k, v in headlines_of(args).items() if isinstance(v, dict) and v.get('owner')}   # his own win
        snap, pics = front_snapshot(front, notes, pool, resolver(data.get('items', [])), {**checked, **mine}, kept_sums, evt,
                                    days.get(dk(now).date().isoformat()),
                                    read(args, 'origin/data', 'places.json', {}).get('places') or {}, now)
        index = archive_index(read(args, 'origin/digest', f'{ARCHIVE}/index.json', {}), snap)
        (out / ARCHIVE).mkdir()
        for name, obj in ((f"{snap['date']}.json", snap), ('index.json', index)):
            (out / ARCHIVE / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    new = sum(x['added'] == notes['created'] for d in days.values() for tp in d['topics'] for x in tp['lines'])
    if args.push:
        push(out, f"Opdatering {dk(now):%d.%m %H.%M}", pics)
    left = [a for a in waiting(args, noted) if a['id'] not in noted['items']] if not answer else []
    print(f"{'Published' if args.push else 'Written to ' + str(out)}: {date_da(now)} kl. {dk(now):%H.%M} · {new} new lines · "
          f"lede {'new' if notes['lede_at'] == notes['created'] else 'kept'} · {len(notes['picks'])} picks · "
          f"{len(notes['moves'])} moves · {len(notes['quotes'])} quotes · {len(sums)} summaries · {len(heads)} headlines · "
          f"Live {(live['day'] or {}).get('level') or 'normal'}"
          f"{' +' + str(len(live['day'].get('take') or [])) if (live['day'] or {}).get('take') else ''}"
          f"{' -' + str(len(live['day'].get('drop') or [])) if (live['day'] or {}).get('drop') else ''} · "
          f"front {('new' if isinstance(draft.get('front'), dict) and 'blocks' in draft['front'] else 'kept') + ' (' + str(len(front['blocks'])) + ' blocks)' if front else 'none'} · "
          f"{'answer ' + answer['nr'] + ' noted · ' if answer else ''}"
          f"calendar {len(kal['items'])}{' (' + str(len(draft['calendar'])) + ' in this update)' if draft.get('calendar') else ''} · "
          f"days: {', '.join(sorted(days))}")
    if dropped_titles:
        print(f"Note: {len(dropped_titles)} earlier headline(s) broke today's rules and were removed – they come back to "
              'be written anew.')
    if left:
        print(f"Note: Hizb ut-Tahrir's answer {left[0]['id']} is still waiting – note it in \"answer\" in the next update.")
    if not front and dk(now).hour >= QUIET_UNTIL:
        print('Note: the front page has no composition of today – the app shows its fixed page; compose one in "front" '
              'in the next update.')
    unheaded = to_head(pool, {**checked, **{k: v for k, v in headlines_of(args).items() if isinstance(v, dict) and v.get('owner')}}, now) if known else []
    if unheaded:
        print(f'Note: {len(unheaded)} stories in Live still wait for your headline – they come first in the next input.')


# ------------------------------------------------------------------ the front-page archive
# The owner, 18/10: 'Bliver forsider snapshottet og gemt på noget tidspunkt?' – 'ja lav et arkiv, men kun ved dagens
# sidste opdatering. så vi får et om dagen'. Every publish with a composition writes the Danish day's front page
# (arkiv/<date>.json on the digest branch) over the one the day's earlier update left, so what stays is the day's last:
# one front page a day, kept for good, arkiv/index.json listing the days. A snapshot holds what the page showed then –
# the composition and the lede, every story it names with the headline and summary it wore, the event pages it placed
# or that the app set in by itself (with their places' coordinates), its quote, the Live block's stories and the day's
# recap –, and Dagens historie's and the events' pictures as their light copies in arkiv/img/: the data branch's own
# picture put in the digest branch's tree, nothing fetched; the outlet's original stays the fallback. The app's
# 'Tidligere forsider' draws it (arkPage in app.js).
ARCHIVE = 'arkiv'
ARCH_LIVE = 3            # the Live block's stories when the block gives no number (the app's nowStrip)
ARCH_EVENT_STORIES = 8   # an event page's stories kept with it
ARCH_ALSO = 6            # the other outlets kept with a story (the opened story's 'Andre medier')


def _first(*xs):
    return next((x for x in xs if x), None)


def arch_story(i, titles, sums):
    """A story as the front page showed it: the editor's headline (else the Danish one, else the outlet's; a curiosity
    headline gives way to its teaser's first sentence, as the app does), its summary, the outlet, its link, its picture."""
    ids = ids_of(i) | {a.get('id') for a in i.get('also') or [] if a.get('id')}
    ed = _first(*[(titles.get(k) or {}).get('title') for k in sorted(ids)],
                *[(v or {}).get('title') for v in titles.values() if set((v or {}).get('members') or []) & ids])
    mine = next(((titles.get(k) or {}).get('title') for k in sorted(ids) if (titles.get(k) or {}).get('owner')), None)
    ed = mine or (ed if ed and good_title(ed) else None)   # the owner's own headline is his: never refused
    lang, own = i.get('lang') or '', clean(i.get('title'))
    if ed:
        title, how = ed, 'ed'
    elif lang == 'da' or not (i.get('title_da') or i.get('title_tr')):
        title, how = own, ''
    else:
        title, how = clean(i.get('title_da') or i.get('title_tr')), 'mt'
    teaser = radar_heads.clean_teaser((i.get('summary_da') if how == 'mt' else None) or i.get('summary') or '', own)
    if how != 'ed' and radar_heads.curious(title) and teaser:
        first = re.match(r'[\s\S]*?[.!?](?=\s|$)', teaser)
        title = clip(first.group(0) if first else teaser, 120)
    danish = how == 'ed' or lang == 'da' or bool(i.get('title_da'))
    q = voice.quote_israel if danish else (lambda s: s)
    out = {'id': i['id'], 'title': q(title), 'source': i.get('source') or '', 'link': i.get('link') or '',
           'published': i.get('published') or i.get('found'), 'sec': i.get('sec') or '', 'lang': lang, 'how': how,
           'summary': q(teaser), 'outlets': i.get('outlets') or 1}
    if own and own != title:
        out['origTitle'] = own   # the outlet's own headline as it wrote it: the opened story's 'Original'
    summary = _first(*[(sums.get(k) or {}).get('text') for k in sorted(ids)])
    if summary:
        out['ed'] = {'text': voice.quote_israel(summary), 'paywall': True}
    for k in ('kind', 'pic', 'pf', 'cover', 'big'):
        if i.get(k):
            out[k] = i[k]
    if i.get('confirmed') == 0:
        out['confirmed'] = 0
    also = [{k: a[k] for k in ('source', 'title', 'title_tr', 'link', 'group', 'lang') if a.get(k)}
            for a in (i.get('also') or [])[:ARCH_ALSO]]
    if also:
        out['also'] = also
    return out


def front_snapshot(front, notes, pool, find, titles, sums, events, day, places, now):
    """(the day's front page as the app drew it, {arkiv/img/<name>: its light copy on the data branch}) – see above."""
    date = dk(now).date().isoformat()
    named, pics = [], {}

    def take(x):
        i = find.get(str(x or ''))
        if i and i['id'] not in named:
            named.append(i['id'])
        return i['id'] if i else None

    by_ev = {e['id']: e for e in (events or {}).get('items') or [] if e.get('id')}
    blocks, placed = [], []
    for b in front.get('blocks') or []:
        if not isinstance(b, dict) or not b.get('kind'):
            continue
        b = dict(b)
        if b['kind'] == 'top':
            b['story'] = take(b.get('story'))
            if not b['story']:
                continue
            if (titles.get(b['story']) or {}).get('owner'):   # the owner's own headline over the front page's
                b.pop('title', None)
            b['with'] = [s for s in map(take, b.get('with') or []) if s]
        elif b['kind'] == 'liste':
            b['stories'] = [s for s in map(take, b.get('stories') or []) if s]
            if not b['stories']:
                continue
        elif b['kind'] == 'citat' and not (b.get('who') and b.get('text')):
            q = next((q for q in notes.get('quotes') or [] if q.get('id') == b.get('quote')), None)
            if not q:
                continue
            b.update({k: q[k] for k in ('who', 'text', 'link', 'sec') if q.get(k)})
        elif b['kind'] in ('begivenhed', 'tal', 'nedtaelling'):
            if b.get('event') not in by_ev:
                continue
            placed.append(b['event'])
        blocks.append(b)
    # the events the app sets in by itself (eventsUnplaced): one under way under Dagens historie, one ahead within a week
    today = dk(now).date()

    def days_to(e):
        try:
            return (datetime.fromisoformat(str(e.get('date') or '')[:10]).date() - today).days
        except ValueError:
            return None
    for e in by_ev.values():
        if e['id'] in placed:
            continue
        d = days_to(e) if e.get('status') == 'kommende' else None
        ahead = d is not None and 0 <= d <= 7
        if e.get('status') == 'i gang' and not any(x.get('auto') == 'i gang' for x in blocks):
            blocks.append({'kind': 'begivenhed', 'event': e['id'], 'auto': 'i gang'})
            placed.append(e['id'])
        elif ahead and not any(x.get('auto') == 'kommende' for x in blocks):
            blocks.append({'kind': 'nedtaelling', 'event': e['id'], 'auto': 'kommende'})
            placed.append(e['id'])
    lede_ids = [take(x) or '' if x else x for x in (front.get('lede_ids') or notes.get('lede_ids') or [])]
    # the Live block: the newest stories no other block shows, as the app picks them
    shown = set(named)
    for b in blocks:
        if b['kind'] == 'live':
            n = max(1, min(10, int(b.get('n') or ARCH_LIVE)))
            fresh = sorted((i for i in pool if i['id'] not in shown and i.get('kind') != 'kommentar' and i.get('confirmed') != 0),
                           key=lambda i: i.get('published') or i.get('found') or '', reverse=True)[:n]
            b['stories'] = [take(i['id']) for i in fresh]
            shown |= set(b['stories'])
    evs = []
    for eid in placed:
        e = dict(by_ev[eid])
        e['stories'] = [s for s in map(take, (e.get('stories') or [])[:ARCH_EVENT_STORIES]) if s]
        kick = str(e.get('kicker') or '').strip().lower()
        geo = {p: places[f'{str(p).strip().lower()}|{kick}'] for p in [*(e.get('places') or []), e.get('kicker')]
               if p and f'{str(p).strip().lower()}|{kick}' in places}   # the kicker's own: the country named on the map
        if geo:
            e['geo'] = geo
        if e.get('pic') and e.get('pl'):
            e['img'] = f"{date}-{e['id']}.jpg"
            pics[f"{ARCHIVE}/img/{e['img']}"] = f"l/{e['pl']}"
        e.pop('pl', None)
        evs.append(e)
    stories = {k: arch_story(find[k], titles, sums) for k in named}
    tops = [b for b in blocks if b['kind'] == 'top']
    for k, b in enumerate(tops):   # the main stories' pictures as they were shown large: Dagens historie's always
        s, i = stories.get(b['story']), find.get(b['story'])
        if s and s.get('pic') and i.get('pl') and (not k or b.get('picture') is not False):
            s['img'] = f"{date}-{s['id']}.jpg"
            pics[f"{ARCHIVE}/img/{s['img']}"] = f"l/{i['pl']}"
    snap = {'date': date, 'at': now.isoformat(timespec='seconds'), 'lede': front.get('lede') or notes.get('lede') or '',
            'lede_ids': lede_ids, 'blocks': blocks, 'stories': stories, 'events': evs}
    if day and day.get('topics'):
        snap['day'] = {k: day[k] for k in ('date', 'title', 'created', 'updates', 'topics') if k in day}
    return snap, pics


def archive_index(current, snap):
    """arkiv/index.json: one row a day, newest first – the day's lede, Dagens historie's headline and its picture."""
    top = next((b for b in snap['blocks'] if b['kind'] == 'top' and b.get('story') in snap['stories']), None)
    s = snap['stories'][top['story']] if top else {}
    row = {'date': snap['date'], 'at': snap['at'], 'lede': snap['lede'], 'head': (top or {}).get('title') or s.get('title') or ''}
    row.update({k: s[k] for k in ('img', 'pic', 'pf') if s.get(k)})
    days = [d for d in (current or {}).get('days') or [] if isinstance(d, dict) and d.get('date') and d['date'] != snap['date']]
    return {'updated': snap['at'], 'days': sorted([row, *days], key=lambda d: d['date'], reverse=True)}


def tree_of(git, root, files, gone, path=''):
    """The tree at `path` in `root` with `files` ({path: blob}) set in and the blobs `gone` names left out."""
    entries = {}
    try:
        for row in git('ls-tree', f"{root}:{path.rstrip('/')}" if path else root).splitlines():
            meta, name = row.split('\t', 1)
            entries[name] = meta
    except subprocess.CalledProcessError:
        pass   # no branch yet, or no such folder on it
    for name in [n for n, m in entries.items() if m.split()[1] == 'blob' and gone(path + n)]:
        entries.pop(name)
    inner = {}
    for p, sha in files.items():
        head, _, rest = p.partition('/')
        if rest:
            inner.setdefault(head, {})[rest] = sha
        else:
            entries[head] = f'100644 blob {sha}'
    for name, sub in inner.items():
        entries[name] = f"040000 tree {tree_of(git, root, sub, gone, path + name + '/')}"
    return git('mktree', data=''.join(f'{m}\t{n}\n' for n, m in sorted(entries.items())).encode())


def push(folder, message, pics=None):
    """One commit on the orphan digest branch: these files, the archive's day (arkiv/) with its pictures – the data
    branch's light copies, {arkiv/img/<name>: its path on the data branch} – and every other file the branch holds as it
    was; the working tree is not touched. A picture of the archive's day that its front page no longer shows goes."""
    def git(*a, data=None):
        return subprocess.run(['git', *a], input=data, capture_output=True, check=True).stdout.decode().strip()
    files = {n: git('hash-object', '-w', str(folder / n)) for n in DIGEST_FILES if (folder / n).exists()}
    days = []
    if (folder / ARCHIVE).is_dir():
        for p in sorted((folder / ARCHIVE).glob('*.json')):
            files[f'{ARCHIVE}/{p.name}'] = git('hash-object', '-w', str(p))
            if p.stem != 'index':
                days.append(p.stem)
    for name, src in (pics or {}).items():
        try:
            sha = git('rev-parse', '--verify', '-q', f'origin/data:{src}')
            subprocess.run(['git', 'cat-file', 'blob', sha], capture_output=True, check=True)   # here (fetched now in a partial clone)
            files[name] = sha
        except subprocess.CalledProcessError:
            pass   # the copy is gone: the app shows the outlet's original
    tree = tree_of(git, 'origin/digest', files,
                   lambda p: p not in files and any(p.startswith(f'{ARCHIVE}/img/{d}-') for d in days))
    env = {'GIT_AUTHOR_NAME': 'Khabar redaktør', 'GIT_AUTHOR_EMAIL': 'redaktor@users.noreply.github.com'}
    env.update(GIT_COMMITTER_NAME=env['GIT_AUTHOR_NAME'], GIT_COMMITTER_EMAIL=env['GIT_AUTHOR_EMAIL'])
    commit = subprocess.run(['git', 'commit-tree', tree, '-m', message], capture_output=True, check=True,
                            env={**os.environ, **env}).stdout.decode().strip()
    git('push', '-f', 'origin', f'{commit}:refs/heads/digest')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['check', 'gate', 'input', 'publish'])
    p.add_argument('file', nargs='?', default=str(WORK / 'update.json'))
    p.add_argument('--dir', help='read the data and digest files from this folder instead of git')
    p.add_argument('--data-dir', help="read the data branch's files from this folder (the radar's state in Actions)")
    p.add_argument('--fire', action='store_true', help='gate: fire the routine when the look calls for an update')
    p.add_argument('--out', help='write the files here (default /tmp/editor/out)')
    p.add_argument('--push', action='store_true', help='commit the files to the digest branch')
    p.add_argument('--now', help='pretend it is this time (ISO 8601)')
    p.add_argument('--audit', action='store_true', help="input: the last day's own text and the chief editor's fields")
    p.add_argument('--okonomi', action='store_true', help="input: the economy editor's material for the Økonomi page")
    p.add_argument('--period', choices=['morgen', 'eftermiddag', 'aften'], help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    {'check': cmd_check, 'gate': cmd_gate, 'input': cmd_input, 'publish': cmd_publish}[args.command](args)


if __name__ == '__main__':
    main()
