"""Tools for the Claude editor, who updates Khabar three times a day (07, 15 and 21 Danish time).

Each update does four things: picks the stories that matter most geopolitically (and, for Danmark, those most useful
in the group's dawah), moves stories that landed in the wrong section, chooses the best statements for quote cards,
and adds the day's most important movements to the recap – short 'Who: what' lines in the style of Al Jazeera's
breaking wire and the group's own 'Politiske nyheder' posts, grouped by topic. A line goes into the day it happened
(Danish date), so at 07 what came before midnight completes yesterday's recap.

    python3 scripts/editor.py input              -> /tmp/editor/input.md: the recap so far, the top stories, the new
                                                    stories and wire lines since the last update, and the format
    python3 scripts/editor.py publish FILE       -> checks the update, fills in links, sources and times, and writes
            [--push] [--out DIR]                    digest.json (the day shown, with the editor's picks, moves and
                                                    quotes) and moves.json (the last 30 days); --push commits both

Reads data.json and lines.json from origin/data and moves.json from origin/digest, or all three from --dir.
Options for test runs: --now ISO."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SECTIONS = {'dk': 'Danmark', 'me': 'Mellemøsten', 'world': 'Verden'}
DAYS = ['mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag']
MONTHS = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober',
          'november', 'december']
KEEP = 30        # days in the archive
MAX_NEW = 14     # lines one update may add: the most important movements, not everything
MAX_TEXT = 220   # characters in a line: one short sentence
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
    if args.dir:
        path = Path(args.dir) / name
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


def recent_days(moves, now):
    """Today's day and yesterday's, as far as they exist: the two an update may add to."""
    today = dk(now).date()
    wanted = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    return [d for d in moves.get('days') or [] if d['date'] in wanted]


def update_times(moves):
    return [t for d in moves.get('days') or [] for t in d.get('updates') or []]


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


TEMPLATE = {
    'lede': '<one Danish sentence of at most about 25 words: the day so far, for the top of the front page>',
    'topics': [{
        'name': "<a topic of today's or yesterday's recap, written exactly as listed, or a new short concrete Danish heading>",
        'section': 'dk | me | world',
        'lines': [{'who': '<who says or reports it>', 'text': '<one short Danish sentence: what happened or was said>',
                   'story': '<the story id, when the line tells a story from the list>',
                   'ids': ['<the wire line id, when it comes from the wire>', '<a second id when two lines say the same>']}],
    }],
    'order': ['<the topic names of the day the lines went to, the most important first>'],
    'picks': [{'id': '<story id from the top stories>', 'why': '<a few words: why it matters geopolitically>'}],
    'moves': [{'id': '<story id in the wrong section>', 'sec': 'dk | me | world'}],
    'quotes': [{'who': '<speaker>', 'text': '<the statement in Danish, one or two sentences>', 'sec': 'dk | me | world',
                'ids': ['<wire line id>'], 'story': '<or a story id>'}],
}


def story_lines(i):
    cover = ', '.join(f'{n} {k}' for k, n in (i.get('cover') or {}).items())
    flags = ' · big' if i.get('big') else ''
    tr = i.get('title_tr')
    out = [f"[{i['id']}] {i.get('sec')} · rank {i.get('rank')}{flags} · {i.get('outlets', 1)} outlets ({cover}) · "
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


def cmd_input(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    data, lines, moves = material(args)
    start = window_start(now, update_times(moves))
    told = {x['id'] for d in recent_days(moves, now) for tp in d['topics'] for x in tp['lines'] if x.get('kind') == 's'}
    items = data.get('items', [])
    stories = sorted((i for i in items if ts(i.get('found') or i['published']) >= start and i['id'] not in told),
                     key=lambda i: -(i.get('rank') or 0))
    top = sorted((i for i in items if now - ts(i.get('published') or i['found']) < timedelta(hours=24)),
                 key=lambda i: -(i.get('rank') or 0))[:70]
    wire = uncovered(lines, moves)
    out = [f'# Material for the {dk(now):%H}.00 update · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time)', '']
    for d in sorted(recent_days(moves, now), key=lambda d: d['date']):
        n = sum(len(tp['lines']) for tp in d['topics'])
        out += [f"## The recap of {date_da(noon(datetime.fromisoformat(d['date'])))} so far – {n} lines", '',
                'Continue a topic by writing its name exactly as here. Lines, newest first: [id] Danish time · who: text', '']
        for tp in d['topics']:
            out.append(f"### {tp['name']} ({tp['section']})")
            out += [f"[{x['id']}] {dk(ts(x['at'])):%d.%m %H.%M} · {x['who'] + ': ' if x['who'] else ''}{x['text']}" for x in tp['lines']]
            out.append('')
    out += ['## Top stories of the last 24 hours – for picks and moves (strongest first)', '',
            'Fields: id · section · rank · outlets · title', '']
    out += [f"[{i['id']}] {i.get('sec')} · rank {i.get('rank')} · {i.get('outlets', 1)} outlets · {i.get('title_tr') or i['title']}"
            for i in top]
    out += ['', f'## Stories since {dk(start):%H.%M} {date_da(start)} – {len(stories)}, strongest first – for recap lines', '',
            'Fields: id · section · rank · big (many outlets) · outlets, by kind of media · confirmed (established '
            'outlets; 0 = only Telegram/YouTube channels, so unconfirmed)', '']
    for i in stories[:100]:
        out += story_lines(i)
    out += [f'## Al Jazeera wire lines since the last update – {len(wire)}, oldest first', '',
            'Fields: [id] Danish date and time · Arabic original (machine English, only a hint)', '']
    for v in wire:
        out.append(f"[{v['i']}] {dk(ts(v['p'])):%d.%m %H.%M} · {v['t']}  ({v.get('tr') or '–'})")
    out += ['', '## Write /tmp/editor/update.json in exactly this shape (UTF-8 JSON)', '',
            json.dumps(TEMPLATE, ensure_ascii=False, indent=1)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'input.md').write_text('\n'.join(out), encoding='utf-8')
    print(f'{WORK / "input.md"}: {len(top)} top stories, {len(stories)} new stories since {dk(start):%H.%M}, '
          f'{len(wire)} wire lines')


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
    """One notification a day, with the evening update: the day's most important line, and how many more."""
    if dk(now).hour < 20:
        return None
    lines = [x for tp in day['topics'] for x in tp['lines']]
    if not lines:
        return None
    x = day['topics'][0]['lines'][0]
    return {'title': f"Khabar · dagens resumé, {dk(now).day}. {MONTHS[dk(now).month - 1]}",
            'body': (f"{x['who']}: {x['text']}" if x['who'] else x['text']) + (f'  (+{len(lines) - 1} mere)' if len(lines) > 1 else '')}


def build(draft, data, lines, moves, now):
    """The updated days and the editor's notes, or a list of problems to fix. A line goes into the day it happened
    (Danish date): at 07 what came before midnight completes yesterday's recap."""
    problems = []
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
    # the editor's notes for the app: stories that matter more, stories in the wrong section, the best statements
    lede = ' '.join(str(draft.get('lede', '')).split())
    if not lede or len(lede) > 220:
        problems.append('lede: one sentence of the day so far is needed (at most about 25 words)')
    picks, fixes, quotes = [], [], []
    for p in (draft.get('picks') or [])[:8]:
        if p.get('id') not in by_id:
            problems.append(f"picks: unknown story id {p.get('id')!r}")
        else:
            picks.append({'id': p['id'], 'why': ' '.join(str(p.get('why', '')).split())[:120]})
    for m in draft.get('moves') or []:
        if m.get('id') not in by_id or m.get('sec') not in SECTIONS:
            problems.append(f'moves: {m!r} needs a known story id and a section dk, me or world')
        else:
            fixes.append({'id': m['id'], 'sec': m['sec']})
    for q in (draft.get('quotes') or [])[:8]:
        who, text = ' '.join(str(q.get('who', '')).split()), ' '.join(str(q.get('text', '')).split())
        src = by_id.get(q.get('story')) if q.get('story') else by_line.get((q.get('ids') or [None])[0])
        if not who or not text or len(text) > 300 or q.get('sec') not in SECTIONS or not src:
            problems.append(f"quotes: '{who}: {text[:40]}' needs who, a short text, a section and a known story or wire id")
        else:
            quotes.append({'who': who, 'text': text, 'sec': q['sec'], 'link': src.get('link') or src.get('u', '')})
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
    notes = {'created': stamp, 'lede': lede, 'picks': picks, 'moves': fixes, 'quotes': quotes}
    return days, notes, []


def cmd_publish(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    draft = json.loads(Path(args.file).read_text(encoding='utf-8'))
    data, lines, moves = material(args)
    days, notes, problems = build(draft, data, lines, moves, now)
    if problems:
        print('Not published – fix these in the file and run publish again:')
        print('\n'.join('- ' + p for p in problems))
        sys.exit(1)
    merged = {d['date']: d for d in moves.get('days') or []}
    merged.update(days)
    archive = sorted(merged.values(), key=lambda d: d['date'], reverse=True)[:KEEP]
    today = days[dk(now).date().isoformat()]
    shown = today if today['topics'] else next((d for d in archive if d['topics']), today)   # early morning: yesterday
    digest = {**shown, 'period': period_of(now), 'whatsapp': day_text(shown), 'push': push_text(shown, now), 'editor': notes}
    files = {'digest.json': digest, 'moves.json': {'updated': notes['created'], 'days': archive}}
    out = Path(args.out) if args.out else WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    new = sum(x['added'] == notes['created'] for d in days.values() for tp in d['topics'] for x in tp['lines'])
    if args.push:
        push(out, f"Opdatering {dk(now):%d.%m %H.%M}")
    print(f"{'Published' if args.push else 'Written to ' + str(out)}: {date_da(now)} kl. {dk(now):%H.%M} · {new} new lines · "
          f"{len(notes['picks'])} picks · {len(notes['moves'])} moves · {len(notes['quotes'])} quotes · "
          f"days: {', '.join(sorted(days))}")


def push(folder, message):
    """One commit on the orphan digest branch holding just the two files; the working tree is not touched."""
    def git(*a, data=None):
        return subprocess.run(['git', *a], input=data, capture_output=True, check=True).stdout.decode().strip()
    tree = git('mktree', data=''.join(
        f"100644 blob {git('hash-object', '-w', str(folder / n))}\t{n}\n" for n in ('digest.json', 'moves.json')).encode())
    env = {'GIT_AUTHOR_NAME': 'Khabar redaktør', 'GIT_AUTHOR_EMAIL': 'redaktor@users.noreply.github.com'}
    env.update(GIT_COMMITTER_NAME=env['GIT_AUTHOR_NAME'], GIT_COMMITTER_EMAIL=env['GIT_AUTHOR_EMAIL'])
    commit = subprocess.run(['git', 'commit-tree', tree, '-m', message], capture_output=True, check=True,
                            env={**os.environ, **env}).stdout.decode().strip()
    git('push', '-f', 'origin', f'{commit}:refs/heads/digest')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['input', 'publish'])
    p.add_argument('file', nargs='?', default=str(WORK / 'update.json'))
    p.add_argument('--dir', help='read data.json, lines.json and moves.json from this folder instead of git')
    p.add_argument('--out', help='write the files here (default /tmp/editor/out)')
    p.add_argument('--push', action='store_true', help='commit the files to the digest branch')
    p.add_argument('--now', help='pretend it is this time (ISO 8601)')
    p.add_argument('--period', choices=['morgen', 'eftermiddag', 'aften'], help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    (cmd_input if args.command == 'input' else cmd_publish)(args)


if __name__ == '__main__':
    main()
