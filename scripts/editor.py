"""Tools for the Claude editor, who keeps Khabar's overview of the day.

One overview per day (Danish time): the day's most important movements as short lines in the style of Al Jazeera's
breaking wire and the group's own 'Politiske nyheder' posts – 'Who: what', one sentence each, grouped by topic. The
editor adds to it at 07, 15 and 22; the first update after midnight starts the next day. The app shows the day at
the bottom of its front page; earlier days stay in an archive.

    python3 scripts/editor.py input              -> /tmp/editor/input.md: the day so far, the stories and every
                                                    Al Jazeera wire line since the last update, and the format
    python3 scripts/editor.py publish FILE       -> checks Claude's additions, fills in links, sources and times,
            [--push] [--out DIR]                    adds them to the day and writes digest.json (the day, with its
                                                    share text) and moves.json (the last 30 days, newest first);
                                                    --push commits both to the digest branch

Reads data.json and lines.json from origin/data and moves.json from origin/digest, or all three from --dir.
Options for test runs: --now ISO, --period morgen|eftermiddag|aften."""
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


def window_start(now, period, times=()):
    """Where the update's stories begin: at the newest earlier update (less than 20 hours old), so an update never
    repeats the one before; without one, at the usual time before it (Danish time): morning since 22:00 the evening
    before, afternoon since 07:00, evening since 15:00."""
    earlier = [ts(t) for t in times if t and timedelta(0) < now - ts(t) < timedelta(hours=20)]
    if earlier:
        return max(earlier)
    local = dk(now)
    if period == 'morgen':
        start = (local - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
    else:
        start = local.replace(hour=7 if period == 'eftermiddag' else 15, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)


# ------------------------------------------------------------------ the day and the archive

def new_day(t):
    return {'date': dk(t).date().isoformat(), 'title': f'Politiske nyheder – {date_da(t)}', 'created': '',
            'updates': [], 'topics': [], 'ids': []}


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


def today_of(moves, now):
    days = moves.get('days') or []
    return days[0] if days and days[0]['date'] == dk(now).date().isoformat() else None


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
    'topics': [{
        'name': "<today's topic name to continue it, or a new short, concrete Danish heading>",
        'section': 'dk | me | world',
        'lines': [{'who': '<who says or reports it>', 'text': '<one short Danish sentence: what happened or was said>',
                   'story': '<the story id, when the line tells a story from the list>',
                   'ids': ['<the wire line id, when it comes from the wire>', '<a second id when two lines say the same>']}],
    }],
    'order': ["<every topic name of the day, today's and new, the most important first>"],
    'drop': ["<optional, rare: ids of today's lines that turned out to be wrong>"],
}


def cmd_input(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    period = args.period or period_of(now)
    data, lines, moves = material(args)
    day = today_of(moves, now)
    start = window_start(now, period, update_times(moves))
    told = {x['id'] for tp in (day or {}).get('topics', []) for x in tp['lines'] if x.get('kind') == 's'}
    stories = [i for i in data.get('items', []) if ts(i.get('found') or i['published']) >= start   # found: a gap must not hide it
               and i['id'] not in told]
    stories.sort(key=lambda i: -(i.get('rank') or 0))
    wire = uncovered(lines, moves)
    out = [f'# Material for the {dk(now).hour}:00 update of the overview · {date_da(now, True)} kl. {dk(now):%H.%M} '
           '(Danish time)', '']
    if day:
        n = sum(len(tp['lines']) for tp in day['topics'])
        out += [f"## Today's overview so far ({date_da(now)}) – {n} lines in {len(day['topics'])} topics", '',
                'Continue a topic by writing its name exactly as here. Lines, newest first: [id] Danish time · who: text', '']
        for tp in day['topics']:
            out.append(f"### {tp['name']} ({tp['section']})")
            out += [f"[{x['id']}] {dk(ts(x['at'])):%H.%M} · {x['who'] + ': ' if x['who'] else ''}{x['text']}" for x in tp['lines']]
            out.append('')
    else:
        out += ["## Today's overview so far – nothing yet", '', f'This update starts the overview of {date_da(now)}.', '']
    out += [f'## Stories since {dk(start):%H.%M} {date_da(start)} – {len(stories)}, strongest first', '',
            'Fields: id · section · rank · big (many outlets) · outlets, by kind of media · confirmed (established '
            'outlets; 0 = only Telegram/YouTube channels, so unconfirmed)', '']
    for i in stories[:90]:
        cover = ', '.join(f'{n} {k}' for k, n in (i.get('cover') or {}).items())
        flags = ' · big' if i.get('big') else ''
        tr = i.get('title_tr')
        out += [f"[{i['id']}] {i.get('sec')} · rank {i.get('rank')}{flags} · {i.get('outlets', 1)} outlets ({cover}) · "
                f"confirmed {i.get('confirmed')}",
                f"{tr} (machine translation from {i.get('lang')}; original: {i['title']})" if tr else i['title']]
        summary = i.get('summary_tr') if tr else i.get('summary')
        if summary:
            out.append(summary)
        out.append(f"{i['source']} · {dk(ts(i.get('published') or i['found'])):%d.%m %H.%M} · {i['link']}")
        also = [f"{a['source']}: {a.get('title_tr') or a['title']}" for a in (i.get('also') or [])[:6]]
        if also:
            out.append('Also: ' + ' | '.join(also))
        out.append('')
    out += [f'## Al Jazeera wire lines since the last update – {len(wire)}, oldest first', '',
            'Fields: [id] Danish time · Arabic original (machine English, only a hint)', '']
    for v in wire:
        out.append(f"[{v['i']}] {dk(ts(v['p'])):%d.%m %H.%M} · {v['t']}  ({v.get('tr') or '–'})")
    out += ['', '## Write /tmp/editor/update.json in exactly this shape (UTF-8 JSON)', '',
            json.dumps(TEMPLATE, ensure_ascii=False, indent=1)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'input.md').write_text('\n'.join(out), encoding='utf-8')
    print(f'{WORK / "input.md"}: {"day so far, " if day else "a new day, "}{len(stories)} stories since '
          f'{dk(start):%H.%M}, {len(wire)} wire lines')


# ------------------------------------------------------------------ publishing an update

def day_text(day):
    """The share text, in the format members post themselves ('Politiske nyheder')."""
    out = [day['title'], '']
    for tp in day['topics']:
        out += [tp['name'], '']
        for x in tp['lines']:
            out += [f"- {x['who']}: {x['text']}" if x['who'] else f"- {x['text']}", '']
    return '\n'.join(out).strip()


def push_text(day):
    """The notification for an update: its most important new line, and how many more came; none when it added
    nothing."""
    new = [x for tp in day['topics'] for x in tp['lines'] if x['added'] == day['created']]
    if not new:
        return None
    body = f"{new[0]['who']}: {new[0]['text']}" if new[0]['who'] else new[0]['text']
    return {'title': f"Khabar · overblik kl. {dk(ts(day['created'])).hour}",
            'body': body + (f'  (+{len(new) - 1} mere)' if len(new) > 1 else '')}


def build(draft, data, lines, moves, now):
    """Today's overview with Claude's additions, or a list of problems to fix."""
    problems = []
    stamp = now.isoformat(timespec='seconds')
    old = today_of(moves, now)
    day = json.loads(json.dumps(old)) if old else new_day(now)
    by_id = {i['id']: i for i in data.get('items', [])}
    wire = {v['i']: v for v in uncovered(lines, moves)}
    told = {x['id'] for tp in day['topics'] for x in tp['lines'] if x.get('kind') == 's'}
    known = {key(tp['name']): tp for tp in day['topics']}
    used, picked, adds = {}, {}, []   # wire id -> where; story id -> where; (name, section, line)
    for k, tp in enumerate(draft.get('topics') or []):
        name = ' '.join(str(tp.get('name', '')).split())
        where = f"topic {k + 1} ({name or '?'})"
        if not name:
            problems.append(f'{where}: no name')
        section = known[key(name)]['section'] if key(name) in known else tp.get('section')
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
                    problems.append(f"{label}: story {story} is in today's overview already")
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
        problems.append(f'{len(adds)} new lines – at most {MAX_NEW}: keep only the most important movements')
    drop = set(draft.get('drop') or [])
    have = {x['id'] for tp in day['topics'] for x in tp['lines']}
    problems += [f"drop: {i!r} is no line in today's overview" for i in sorted(drop - have)]
    names = {key(tp['name']) for tp in day['topics']} | {key(n) for n, _, _ in adds}
    order = [n for n in draft.get('order') or [] if str(n).strip()]
    problems += [f'order: {n!r} is no topic of the day' for n in order if key(n) not in names]
    if problems:
        return None, problems
    for tp in day['topics']:
        tp['lines'] = [x for x in tp['lines'] if x['id'] not in drop]
    for name, section, line in adds:
        topic_of(day, name, section)['lines'].append(line)
    for tp in day['topics']:
        newest_first(tp)
    rank = {key(n): j for j, n in enumerate(order)}
    day['topics'] = sorted((tp for tp in day['topics'] if tp['lines']), key=lambda tp: rank.get(key(tp['name']), len(rank)))
    day['ids'] = sorted(set(day['ids']) | set(wire))   # every line it was given, used or not, is done
    day['updates'] = day['updates'] + [stamp]
    day['created'] = stamp
    return day, []


def cmd_publish(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    period = args.period or period_of(now)
    draft = json.loads(Path(args.file).read_text(encoding='utf-8'))
    data, lines, moves = material(args)
    day, problems = build(draft, data, lines, moves, now)
    if problems:
        print('Not published – fix these in the file and run publish again:')
        print('\n'.join('- ' + p for p in problems))
        sys.exit(1)
    days = [day] + [d for d in moves.get('days') or [] if d['date'] != day['date']][:KEEP - 1]
    digest = {**day, 'period': period, 'whatsapp': day_text(day), 'push': push_text(day)}
    files = {'digest.json': digest, 'moves.json': {'updated': day['created'], 'days': days}}
    out = Path(args.out) if args.out else WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    new = sum(x['added'] == day['created'] for tp in day['topics'] for x in tp['lines'])
    if args.push:
        push(out, f"Overblik {dk(now):%d.%m %H.%M}")
    print(f"{'Published' if args.push else 'Written to ' + str(out)}: {date_da(now)} kl. {dk(now):%H.%M} · {new} new lines · "
          f"{sum(len(tp['lines']) for tp in day['topics'])} in the day · topics: {', '.join(tp['name'] for tp in day['topics'])}")


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
    p.add_argument('--period', choices=['morgen', 'eftermiddag', 'aften'])
    args = p.parse_args(argv)
    (cmd_input if args.command == 'input' else cmd_publish)(args)


if __name__ == '__main__':
    main()
