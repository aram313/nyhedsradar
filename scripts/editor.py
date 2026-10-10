"""Tools for the Claude editor, which writes Khabar's overview three times a day (07, 15 and 22 Danish time).

One edition = the period's most important stories, each with a short summary, grouped by topic, and under
each topic what the actors say: every line of Al Jazeera's Arabic breaking wire since the previous edition,
translated into Danish. The app shows the newest edition on its front page; earlier ones stay in an archive.

    python3 scripts/editor.py input              -> /tmp/editor/input.md: the period's stories and every wire
                                                    line no edition has covered yet, and the format to write
    python3 scripts/editor.py publish FILE       -> checks Claude's edition, adds links, sources and the share
            [--push] [--out DIR]                    texts, writes digest.json (newest edition) and moves.json
                                                    (all editions, newest first, 45 kept, earlier ones never
                                                    changed); --push commits both to the digest branch

Reads data.json and lines.json from origin/data and moves.json from origin/digest, or all three from --dir.
Options for test runs: --now ISO, --period morgen|eftermiddag|aften, --created ISO."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SECTIONS = {'dk': 'DANMARK', 'me': 'MELLEMØSTEN', 'world': 'VERDEN'}
DAYS = ['mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag']
MONTHS = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober',
          'november', 'december']
KEEP = 45   # three editions a day: about two weeks
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


def span_da(a, b):
    """'10. oktober 2026', '9. og 10. oktober 2026' or '31. oktober og 1. november 2026'."""
    a, b = dk(a), dk(b)
    if a.date() == b.date():
        return date_da(a)
    if (a.year, a.month) == (b.year, b.month):
        return f'{a.day}. og {b.day}. {MONTHS[b.month - 1]} {b.year}'
    return f'{a.day}. {MONTHS[a.month - 1]} og {date_da(b)}'


def period_of(now):
    h = dk(now).hour
    return 'morgen' if h < 12 else 'eftermiddag' if h < 17 else 'aften'


def window_start(now, period, editions=()):
    """Where the period's stories begin: at the newest earlier edition (less than 20 hours old), so the 15 and 22
    editions do not repeat the one before; without one, at the usual time before it (Danish time): morning since
    22:00 the evening before, afternoon since 07:00, evening since 15:00."""
    earlier = [ts(e['created']) for e in editions if e.get('created') and timedelta(0) < now - ts(e['created']) < timedelta(hours=20)]
    if earlier:
        return max(earlier)
    local = dk(now)
    if period == 'morgen':
        start = (local - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
    else:
        start = local.replace(hour=7 if period == 'eftermiddag' else 15, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)


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
    return (read(args, 'origin/data', 'data.json', {'items': []}), read(args, 'origin/data', 'lines.json', {'items': []}),
            read(args, 'origin/digest', 'moves.json', {'briefs': []}))


def uncovered(lines, editions):
    """Every wire line no earlier edition has covered, oldest first. An edition lists the lines it covered in
    `ids`; the very first editions had no list and covered everything published up to their `until`."""
    done, upto = set(), ''
    for e in editions:
        if 'ids' in e:
            done.update(e['ids'])
        else:
            upto = max(upto, e.get('until') or e.get('created') or '')
    wire = [v for v in lines.get('items', []) if v.get('k') == 'w' and v['i'] not in done
            and not (upto and ts(v['p']) <= ts(upto))]
    return sorted(wire, key=lambda v: v['p'])


TEMPLATE = {
    'intro': '<1-2 Danish sentences: the most important of the period>',
    'topics': [{
        'name': '<concrete Danish heading: a country, conflict, negotiation or Danish issue>',
        'section': 'dk | me | world',
        'stories': [{'id': '<story id from the list>', 'headline': '<max ~10 words>', 'text': '<2-3 sentences>'}],
        'lines': [{'ids': ['<wire line id>', '<a second id when two lines say the same>'], 'who': '<speaker>',
                   'text': '<the statement in Danish>'}],
    }],
    'skipped': ['<ids of wire lines left out: only sport, weather and pure repetition>'],
}


def cmd_input(args):
    now = ts(args.now) if args.now else datetime.now(timezone.utc)
    period = args.period or period_of(now)
    data, lines, moves = material(args)
    start = window_start(now, period, moves.get('briefs', []))
    stories = [i for i in data.get('items', []) if ts(i.get('found') or i['published']) >= start]   # found: a gap must not hide it
    stories.sort(key=lambda i: -(i.get('rank') or 0))
    wire = uncovered(lines, moves.get('briefs', []))
    out = [f'# Material for the {period} edition · {date_da(now, True)} kl. {dk(now):%H.%M} (Danish time)', '',
           f'## Stories since {dk(start):%H.%M} {date_da(start)} – {len(stories)}, strongest first', '',
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
    out += [f'## Al Jazeera wire lines to translate – {len(wire)}, oldest first', '',
            'Fields: [id] Danish time · Arabic original (machine English, only a hint)', '']
    for v in wire:
        out.append(f"[{v['i']}] {dk(ts(v['p'])):%d.%m %H.%M} · {v['t']}  ({v.get('tr') or '–'})")
    out += ['', '## Write /tmp/editor/edition.json in exactly this shape (UTF-8 JSON)', '',
            json.dumps(TEMPLATE, ensure_ascii=False, indent=1)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'input.md').write_text('\n'.join(out), encoding='utf-8')
    print(f'{WORK / "input.md"}: {len(stories)} stories since {dk(start):%H.%M}, {len(wire)} wire lines to translate')


# ------------------------------------------------------------------ publishing an edition

def overview_text(ed):
    out = [f"*Dagens overblik – {ed['period']}, {date_da(ts(ed['created']), True)}*", '', ed['intro'], '']
    n = 0
    for sec, name in SECTIONS.items():
        mine = [s for tp in ed['topics'] for s in tp.get('stories', []) if s['section'] == sec]
        if mine:
            out += [name, '']
            for s in mine:
                n += 1
                out += [f"{n}. *{s['headline']}*", s['text'], s['link'], '']
    return '\n'.join(out).strip()


def lines_text(ed):
    out = [ed['title'], '']
    for tp in ed['topics']:
        if tp.get('lines'):
            out += [tp['name'], '']
            for line in tp['lines']:
                out += [f"- {line['who']}: {line['text']}", '']
    return '\n'.join(out).strip()


def build(draft, data, lines, moves, now, period):
    """The finished edition from Claude's draft, or a list of problems to fix."""
    problems = []
    by_id = {i['id']: i for i in data.get('items', [])}
    wire = {v['i']: v for v in uncovered(lines, moves.get('briefs', []))}
    used, picked = {}, {}   # wire line id -> where it went; story id -> where it went
    if not str(draft.get('intro', '')).strip():
        problems.append('intro is empty')
    topics = []
    for k, tp in enumerate(draft.get('topics') or []):
        where = f"topic {k + 1} ({tp.get('name', '?')})"
        if not str(tp.get('name', '')).strip():
            problems.append(f'{where}: no name')
        if tp.get('section') not in SECTIONS:
            problems.append(f"{where}: section must be dk, me or world, not {tp.get('section')!r}")
        stories = []
        for s in tp.get('stories') or []:
            it = by_id.get(s.get('id'))
            if not it:
                problems.append(f"{where}: unknown story id {s.get('id')!r}")
                continue
            if s['id'] in picked:
                problems.append(f"{where}: story {s['id']} is used twice (also in {picked[s['id']]})")
            picked[s['id']] = where
            if not str(s.get('headline', '')).strip() or not str(s.get('text', '')).strip():
                problems.append(f"{where}: story {s['id']} needs a headline and a text")
            stories.append({'id': it['id'], 'headline': s.get('headline', '').strip(), 'text': s.get('text', '').strip(),
                            'link': it['link'], 'source': it['source'], 'confirmed': it.get('confirmed', 1),
                            'section': tp.get('section')})
        out_lines = []
        for line in tp.get('lines') or []:
            ids = line.get('ids') or ([line['id']] if line.get('id') else [])
            if not ids:
                problems.append(f"{where}: the line {line.get('who', '?')}: … has no ids")
            for i in ids:
                if i not in wire:
                    problems.append(f'{where}: {i!r} is no wire line of this edition')
                elif i in used:
                    problems.append(f'{where}: wire line {i} is used twice (also in {used[i]})')
                used[i] = where
            if not str(line.get('who', '')).strip() or not str(line.get('text', '')).strip():
                problems.append(f'{where}: every line needs who and text')
            first = wire.get(ids[0]) if ids else None
            out_lines.append({'who': line.get('who', '').strip(), 'text': line.get('text', '').strip(),
                              'link': first['u'] if first else '', 'id': ids[0] if ids else ''})
        if not stories and not out_lines:
            problems.append(f'{where}: no stories and no lines')
        topics.append({'name': tp.get('name', '').strip(), 'section': tp.get('section'), 'stories': stories,
                       'lines': out_lines})
    if not topics:
        problems.append('no topics')
    for i in draft.get('skipped') or []:
        if i not in wire:
            problems.append(f'skipped: {i!r} is no wire line of this edition')
        used.setdefault(i, 'skipped')
    missing = [v for i, v in wire.items() if i not in used]
    for v in missing:
        problems.append(f"wire line {v['i']} ({dk(ts(v['p'])):%H.%M}) is missing – translate it into a topic, or list it "
                        f"in skipped only if it is sport, weather or pure repetition: {v.get('tr') or v['t']}")
    if problems:
        return None, problems
    covered = [wire[i] for i in used]
    first = min((ts(v['p']) for v in covered), default=window_start(now, period, moves.get('briefs', [])))
    last = max((ts(v['p']) for v in covered), default=now)
    ed = {'created': now.isoformat(timespec='seconds'), 'period': period, 'intro': draft['intro'].strip(),
          'title': f'Politiske nyheder – {span_da(first, last)}', 'from': first.isoformat(timespec='seconds'),
          'until': last.isoformat(timespec='seconds'), 'topics': topics, 'ids': sorted(used)}
    return ed, []


def cmd_publish(args):
    now = ts(args.created or args.now) if (args.created or args.now) else datetime.now(timezone.utc)
    period = args.period or period_of(now)
    draft = json.loads(Path(args.file).read_text(encoding='utf-8'))
    data, lines, moves = material(args)
    ed, problems = build(draft, data, lines, moves, now, period)
    if problems:
        print('Not published – fix these in the file and run publish again:')
        print('\n'.join('- ' + p for p in problems))
        sys.exit(1)
    earlier = [e for e in moves.get('briefs', []) if e.get('created') != ed['created']]
    digest = {**ed, 'items': [s for tp in ed['topics'] for s in tp['stories']],
              'whatsapp': overview_text(ed), 'lines_whatsapp': lines_text(ed)}
    files = {'digest.json': digest, 'moves.json': {'updated': ed['created'], 'briefs': [ed] + earlier[:KEEP - 1]}}
    out = Path(args.out) if args.out else WORK / 'out'
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    n_lines = sum(len(tp['lines']) for tp in ed['topics'])
    n_stories = len(digest['items'])
    if args.push:
        push(out, f"Overblik {ed['period']} {dk(now):%d.%m %H.%M}")
    print(f"{'Published' if args.push else 'Written to ' + str(out)}: {ed['period']} · {n_stories} stories · "
          f"{n_lines} lines ({len(ed['ids'])} wire lines covered) · topics: {', '.join(tp['name'] for tp in ed['topics'])}")


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
    p.add_argument('file', nargs='?', default=str(WORK / 'edition.json'))
    p.add_argument('--dir', help='read data.json, lines.json and moves.json from this folder instead of git')
    p.add_argument('--out', help='write the files here (default /tmp/editor/out)')
    p.add_argument('--push', action='store_true', help='commit the files to the digest branch')
    p.add_argument('--now', help='pretend it is this time (ISO 8601)')
    p.add_argument('--created', help='the edition\'s time stamp (re-publishing an edition)')
    p.add_argument('--period', choices=['morgen', 'eftermiddag', 'aften'])
    args = p.parse_args(argv)
    (cmd_input if args.command == 'input' else cmd_publish)(args)


if __name__ == '__main__':
    main()
