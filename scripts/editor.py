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
                                                    a new answer of Hizb ut-Tahrir), the front page now and a verdict,
                                                    INTET NYT AF VÆGT or OPDATÉR: why. The routine stops there or
                                                    updates.
    python3 scripts/editor.py input              -> /tmp/editor/input.md: the brain (scripts/brain.py), the front page
                                                    now, the recap so far, the top stories, the new stories and wire
                                                    lines since the last update, a new answer to note, and the format
    python3 scripts/editor.py publish FILE       -> checks the update, fills in links, sources and times, and writes
            [--push] [--out DIR]                    digest.json (the day shown, with the editor's picks, moves and
                                                    quotes), moves.json (the last 30 days), summaries.json (the story
                                                    summaries and checked Danish headlines of the last 4 days) and
                                                    answers.json (Hizb ut-Tahrir's answers noted after the static
                                                    layer, kept forever); --push commits them to the digest branch

Each update weighs the news by the brain – the books' order of weight and Hizb ut-Tahrir's newest answers, used only to
choose and order: the lede, the picks, Dagens historie and the order of the recap's topics. The app shows no analysis;
the editor's own text (lede, recap lines, summaries, headlines) stays reality. An update writes the lede, picks,
quotes, short summaries of the stories readers open, the Danish of the strongest foreign headlines, and 'Who: what'
lines for the day's recap in the style of Al Jazeera's wire and the group's own 'Politiske nyheder' posts, grouped by
topic; a line goes into the day it happened (Danish date), so after midnight what came before completes yesterday's
recap. It may keep the lede, the picks and the quotes (leave them out, or write "keep"), add only recap lines, or give
only a new lede. Moves (a story in a clearly wrong section) are rare and stay until undone. Only the first update at
or after 21 Danish time notifies the phones.

Reads data.json, lines.json, items.json and analyses.json from origin/data (or --data-dir, the radar's state folder
in Actions) and digest.json, moves.json, summaries.json and answers.json from origin/digest, or all of them from --dir.
Options for test runs: --now ISO."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain  # noqa: E402 – the books' order of weight and Hizb ut-Tahrir's newest answers, for weighing
import voice  # noqa: E402 – Khabar's content rules

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
MAX_TITLES = 8   # foreign headlines one update goes over in Danish: the strongest the app shows
TITLE_LEN = 140  # characters in a headline
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
CHECK_STORIES = 12   # stories of weight the check lists
CHECK_WIRE = 4       # newest wire lines the check shows
ANSWER_TEXT = 32000  # characters of a new answer's text in the input (the answers run to about 28,000)
ANSWER_KINDS = ('stilling', 'forhold', 'plan', 'fremgangsmåde', 'rolle', 'tilstand', 'motiv')
MAX_READINGS = 15
READING_LEN = 420
NOTE_LEN = 1200
SUBJECT_ID = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*(?:--[a-z0-9]+(?:-[a-z0-9]+)*)?$')
KEEP_WORD = 'keep'
DIGEST_FILES = ('digest.json', 'moves.json', 'summaries.json', 'answers.json')
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


def to_check(items, done, now):
    """The foreign headlines readers see in the machine's Danish: the strongest of each section in the last day,
    then the rest by rank – those the editor has not gone over yet, at most MAX_TITLES."""
    return strongest([i for i in items if day_old(i, now) and i.get('title_da') and i.get('lang') != 'da'
                      and i['id'] not in done], 12, MAX_TITLES)


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


# ------------------------------------------------------------------ check: is there anything to adjust?

def ago(delta):
    m = int(delta.total_seconds() // 60)
    return f'{m} min' if m < 60 else f'{m // 60} t {m % 60:02d} min'


def weighty_big(r):
    """A big story calls for an update when it weighs: of tiers 1-10 by the books' order, or Danish (Danish politics is
    never buried) – a big story of the rest (tier 11) or weighed down (13) waits for the next update."""
    i, t = r[0], r[1]
    return bool(i.get('big')) and (t is None or t <= 10 or i.get('sec') == 'dk')


def verdict(now, last, times, rows, answer, wire=(), covered=(), still=None):
    """The reasons for a full update now, the most pressing first (empty: nothing of weight since the last). covered: the
    stories already a pick or in the recap – they call for no update of their own. still: how long the radar has not
    run, when that is longer than RADAR_STILL."""
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
    out = [f'Khabar check · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time) · '
           + ((f'radar last ran {ago(now - radar_at)} ago' + (' – STOPPED' if still else '')) if radar_at else 'radar: no time'),
           f'Last full update: {dk(last):%d.%m %H.%M} ({ago(now - last)} ago)' if last else 'Last full update: none in the archive',
           f"New since {dk(since):%H.%M}: {sum(1 for r in news if r[3])} stories, {sum(1 for r in news if not r[3])} grew · "
           f"{len(rows)} of weight (tier 1-5, big or 3+ outlets) · {len(wire)} wire lines · "
           f"{'a new answer of Hizb ut-Tahrir' if queue else 'no new answer'}"]
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
    reasons = verdict(now, last, times, rows, answer, wire, set(picked) | recapped, still)
    out.append(('OPDATÉR: ' + '; '.join(reasons)) if reasons else 'INTET NYT AF VÆGT')
    seen = first_seen(args)
    keys = [f"big:{story_key(r[0], seen)}" for r in rows if weighty_big(r) and r[0]['id'] not in picked and r[0]['id'] not in recapped]
    keys += [f"tier:{story_key(r[0], seen)}" for r in rows if r[1] is not None and r[1] <= 3 and (r[0].get('outlets') or 1) >= 2
             and not r[0].get('big') and r[0]['id'] not in picked and r[0]['id'] not in recapped]
    if answer:
        keys.append(f"answer:{answer['id']}")
    facts = {'last': last, 'radar': radar_at, 'keys': keys, 'reasons': reasons}
    return out, reasons, facts


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
    'lede': '<one Danish sentence of at most about 25 words: the day so far, its heaviest movements first – reality only; '
            'leave the field out (or "keep") to keep the lede on the front page>',
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
                'ids': ['<wire line id>'], 'story': '<or a story id>'}],
    'titles': [{'id': '<story id from "Danish headlines to check">',
                'title': '<the headline in correct, natural Danish – the machine\'s own when it is right>'}],
    'summaries': [{'id': '<story id from "Stories to summarise">',
                   'text': '<2-3 Danish sentences from the headline, the teaser and the other outlets: what happened, who, why it matters>',
                   'paywall': True}],
}
ANSWER_TEMPLATE = {'answer': {
    'nr': "<the answer's number, as given>", 'date': 'YYYY-MM-DD',
    'title_da': '<the title in Danish, as the movement titles it: "Svar på spørgsmål: …">',
    'question_da': '<the question in one or two Danish sentences>',
    'note_da': '<2-4 Danish sentences beginning "Ifølge Hizb ut-Tahrirs svar af d/m/åååå …": what it reads and expects>',
    'readings': [{'subject': '<a subject id from the list, or a new lowercase-with-hyphens id; a relation: a--b>',
                  'kind': ' | '.join(ANSWER_KINDS), 'object': '<the other subject, e.g. the patron – optional>',
                  'value': '<a short label, e.g. underordnet – optional>',
                  'text_da': '<one sentence beginning "Ifølge Hizb ut-Tahrirs svar af d/m/åååå …">'}],
    'begreber': ['<the ids of the concepts, states and groups it treats>']}}
SMALL = [
    '## How small an update can be', '',
    'Leave out "lede", "picks" or "quotes" (or write "keep") and they stay as they are on the front page. An update may',
    'add only recap lines, or give only a new lede. Write a new lede when the weight of the day has changed – a story of',
    'a heavier tier, a development that moved – never only to vary the words; new picks when a heavier story has come.',
    '"moves" stay until undone (move the story back to its own section); "summaries" and "titles" are kept four days.', '',
]


def story_lines(i, joined=0):
    cover = ', '.join(f'{n} {k}' for k, n in (i.get('cover') or {}).items())
    flags = ' · big' if i.get('big') else ''
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


def front_lines(notes, digest, by_id):
    """The front page as it is now, so an update can keep what still holds."""
    out = ['## The front page now – keep what still holds', '']
    lede_at = notes.get('lede_at') or notes.get('created')
    out.append(f"Lede (written {dk(ts(lede_at)):%d.%m %H.%M}): {notes['lede']}" if notes.get('lede') and lede_at else 'Lede: none yet')
    tp = main_topic(digest)
    out.append(f"Dagens historie: {tp['name']}" if tp else 'Dagens historie: none yet (the first topic with three lines becomes it)')
    for k, p in enumerate([p for p in notes.get('picks') or [] if p.get('id') in by_id], 1):
        i = by_id[p['id']]
        t = brain.tier_of(i)
        out.append(f"Pick {k}: [{i['id']}]{f' tier {t} ·' if t is not None else ''} {clip(headline(i), 110)}")
    out.append(f"Quotes: {len(notes.get('quotes') or [])} · moves: {len(notes.get('moves') or [])}")
    return out + ['']


def answer_lines(a, known):
    """Hizb ut-Tahrir's new answer, with its text and how to note it."""
    date = str(a.get('date') or '')[:10]
    said = f'Ifølge Hizb ut-Tahrirs svar af {brain.d_slash(date)}' if date else 'Ifølge Hizb ut-Tahrirs svar af d/m/åååå'
    return [
        '## Hizb ut-Tahrir\'s new answer – note it in "answer" (once: it is kept for the concept pages)', '',
        f"nr {a['id']} · {date} · {clean(a.get('title'))} · {a.get('url') or ''}", '',
        'Write the "answer" object (shape below) from this text. Everything in it is the movement\'s reading, attributed: '
        f'note_da (2-4 sentences: what the answer reads and expects) and every reading begin "{said} …". The newest '
        'answer governs: where it reads a state, a power or a relation differently from its current reading in the brain, '
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


def cmd_input(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
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
    heads = to_check(items, set((summaries_of(args).get('titles') or {})), now)
    if heads:
        out += [f'## Danish headlines to check – {len(heads)} (the app shows foreign headlines in Danish; these are machine translations)', '',
                "For each: read the original and the machine's Danish, and write the headline as a Danish news desk would:",
                'the same facts and the same weight, natural Danish word order, names in their usual Danish spelling',
                '(Zelenskyj, Netanyahu, Hizbollah, Hamas), no additions and no opinion, at most about 110 characters. When the',
                "machine's is right, give it unchanged. Fields: [id] language · original (English for Arabic and Turkish) → machine Danish", '']
        out += [f"[{i['id']}] {i.get('lang')} · {i['title']}{' (English: ' + i['title_tr'] + ')' if i.get('title_tr') else ''} → {i['title_da']}"
                for i in heads] + ['']
    out += [f'## Al Jazeera wire lines since the last update – {len(wire)}, oldest first', '',
            'Fields: [id] Danish date and time · Arabic original (machine English, only a hint)', '']
    for v in wire:
        out.append(f"[{v['i']}] {dk(ts(v['p'])):%d.%m %H.%M} · {v['t']}  ({v.get('tr') or '–'})")
    queue = waiting(args, noted)
    template = dict(TEMPLATE)
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


def build(draft, data, lines, moves, now, previous=None):
    """The updated days and the editor's notes, or a list of problems to fix. A line goes into the day it happened
    (Danish date): after midnight what came before completes yesterday's recap. previous: the editor's notes on the
    front page now – the lede, picks and quotes an update leaves out stay, and moves stay until undone."""
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
            voice.check_reality(text, label, problems)
            if not story and not ids:
                problems.append(f'{label} has neither a story id nor wire ids')
            it = None
            if story:
                it = by_id.get(story)
                if not it:
                    problems.append(f'{label}: unknown story id {story!r}')
                elif story in told:
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
                picks.append({'id': p['id'], 'why': why})
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
                quotes.append({'who': who, 'text': text, 'sec': q['sec'], 'link': src.get('link') or src.get('u', '')})
    heads = []
    for x in (draft.get('titles') or [])[:MAX_TITLES + 10]:
        title = ' '.join(str(x.get('title', '')).split())
        if x.get('id') not in by_id:
            problems.append(f"titles: unknown story id {x.get('id')!r}")
        elif not title or len(title) > TITLE_LEN:
            problems.append(f"titles: {x['id']} needs one Danish headline (at most {TITLE_LEN} characters, not {len(title)})")
        else:
            voice.check_voice(title, f"titles: {x['id']}", problems)
            heads.append({'id': x['id'], 'title': title})
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
            voice.check_reality(text, f"summaries: {x['id']}", problems)
            sums.append({'id': x['id'], 'text': text, 'paywall': bool(x.get('paywall'))})
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
    notes = {'created': stamp, 'lede': lede, 'lede_at': lede_at, 'picks': picks, 'moves': list(fixes.values()),
             'quotes': quotes, 'summaries': sums, 'titles': heads}
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
    Everything in it is the movement's reading, attributed – note_da and every reading say 'Ifølge Hizb ut-Tahrirs svar
    af d/m/åååå' with the answer's own date – and the content rules hold (voice.py)."""
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
    said = f'Ifølge Hizb ut-Tahrirs svar af {brain.d_slash(date)}'
    title, question, note = (clean(obj.get(f)) for f in ('title_da', 'question_da', 'note_da'))
    if not title or len(title) > 200:
        problems.append(f'{where}: title_da – the title in Danish, at most 200 characters')
    if not question or len(question) > 600:
        problems.append(f'{where}: question_da – the question in one or two Danish sentences, at most 600 characters')
    if not note or len(note) > NOTE_LEN:
        problems.append(f'{where}: note_da – 2-4 Danish sentences, at most {NOTE_LEN} characters')
    elif said not in note:
        problems.append(f"{where}: note_da must say '{said} …' – the movement's reading, attributed")
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
        elif said not in text:
            problems.append(f"{at}: text_da must say '{said} …'")
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


def digest_head():
    """The digest branch's commit as this checkout knows it ('' when there is none)."""
    try:
        return subprocess.run(['git', 'rev-parse', '--verify', '-q', 'origin/digest'], capture_output=True,
                              check=True).stdout.decode().strip()
    except (subprocess.CalledProcessError, OSError):
        return ''


def cmd_publish(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    draft = json.loads(Path(args.file).read_text(encoding='utf-8'))
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
    current = read(args, 'origin/digest', 'digest.json', {})
    days, notes, problems = build(draft, data, lines, moves, now, current.get('editor') or {})
    noted = answers_of(args)
    answer = None
    if draft.get('answer'):
        answer, more = check_answer(draft['answer'], {str(a['id']): a for a in waiting(args, noted)},
                                    brain.known_ids() | used_ids(noted))
        problems += more
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
    recent = lambda d: {k: v for k, v in (d or {}).items() if now - ts(v['at']) < timedelta(days=SUM_DAYS)}  # noqa: E731
    kept_sums, checked = recent(before.get('items')), recent(before.get('titles'))
    kept_sums.update({x['id']: {'text': x['text'], 'paywall': x['paywall'], 'at': notes['created']} for x in sums})
    checked.update({x['id']: {'title': x['title'], 'at': notes['created']} for x in heads})
    if answer:
        noted['items'][answer['nr']] = answer
    digest = {**shown, 'period': period_of(now), 'whatsapp': day_text(shown), 'push': push_text(shown, now), 'editor': notes}
    files = {'digest.json': digest, 'moves.json': {'updated': notes['created'], 'days': archive},
             'summaries.json': {'updated': notes['created'], 'items': kept_sums, 'titles': checked},
             'answers.json': {'items': dict(sorted(noted['items'].items(), key=lambda kv: str(kv[1].get('date') or ''),
                                                   reverse=True))}}
    out = Path(args.out) if args.out else WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    new = sum(x['added'] == notes['created'] for d in days.values() for tp in d['topics'] for x in tp['lines'])
    if args.push:
        push(out, f"Opdatering {dk(now):%d.%m %H.%M}")
    left = [a for a in waiting(args, noted) if a['id'] not in noted['items']] if not answer else []
    print(f"{'Published' if args.push else 'Written to ' + str(out)}: {date_da(now)} kl. {dk(now):%H.%M} · {new} new lines · "
          f"lede {'new' if notes['lede_at'] == notes['created'] else 'kept'} · {len(notes['picks'])} picks · "
          f"{len(notes['moves'])} moves · {len(notes['quotes'])} quotes · {len(sums)} summaries · {len(heads)} headlines · "
          f"{'answer ' + answer['nr'] + ' noted · ' if answer else ''}days: {', '.join(sorted(days))}")
    if left:
        print(f"Note: Hizb ut-Tahrir's answer {left[0]['id']} is still waiting – note it in \"answer\" in the next update.")


def push(folder, message):
    """One commit on the orphan digest branch: these files, and every other file the branch holds as it was; the
    working tree is not touched."""
    def git(*a, data=None):
        return subprocess.run(['git', *a], input=data, capture_output=True, check=True).stdout.decode().strip()
    entries = {}
    try:
        for row in git('ls-tree', 'origin/digest').splitlines():
            meta, name = row.split('\t', 1)
            entries[name] = meta
    except subprocess.CalledProcessError:
        pass
    for n in DIGEST_FILES:
        if (folder / n).exists():
            entries[n] = f"100644 blob {git('hash-object', '-w', str(folder / n))}"
    tree = git('mktree', data=''.join(f'{meta}\t{name}\n' for name, meta in sorted(entries.items())).encode())
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
    p.add_argument('--period', choices=['morgen', 'eftermiddag', 'aften'], help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    {'check': cmd_check, 'gate': cmd_gate, 'input': cmd_input, 'publish': cmd_publish}[args.command](args)


if __name__ == '__main__':
    main()
