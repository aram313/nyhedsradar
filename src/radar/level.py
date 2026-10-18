"""How much of the candidate pool Live shows (the owner's rule of 2026-10-17, docs/hjerne/notes-owner-volume.md).

The editor sets the day's level – 'få' (a quiet day: only the sharpest), 'normal' (the day's most important; the
default) or 'mange' (a heavy day) – and may take a single story in ('take') or out ('drop') in live.json on the digest
branch. The radar applies it at every pass, so a strong story reaches Live at once:

- a level is a rank floor and a soft count for the last 24 hours (config/settings.json `live_levels`): a story is
  admitted when its rank reaches the floor and fewer than `count` stories of the last 24 hours rank above it. A quiet
  day is never padded (the floor holds), and a story once admitted stays while its rank stays within `live_keep_margin`
  of the line (the floor, or the rank of the last story the count let in), so Live does not flicker when a stronger
  story comes in – which is why the count is soft;
- a big story, and Danish politics on Islam, Muslims, integration and foreign policy, is never cut (`protect`);
- take admits a story of the pool, drop removes one (even a big one: the editor's decision); an id matches a story when
  it is the story's id or one of its members;
- the level holds for the Danish day it was set for: between 00 and 06 the evening's level holds until the editor's
  first update of the day; no live.json, no plan for today, or a file not written for `STALE` between 06 and 24 (the
  editor has stopped: its updates come at most about two hours apart) → level 'normal' (take and drop still apply:
  they are decisions about single stories);
- take and drop of the two days the editor keeps: for one story the newest decision wins (today's take undoes
  yesterday's drop, and the reverse); on the same day drop wins.

The stories older than 24 hours (up to 48, the app's window) keep the admission they had: the radar remembers every
admitted story's members in state/admitted.json."""
from datetime import date, datetime, timedelta

LEVELS = ('få', 'normal', 'mange')
DEFAULT = 'normal'
STALE = timedelta(hours=6)   # the front page's own limit (FRONT_STALE): longer than any gap between the editor's updates
MAX_IDS = 300   # take/drop ids read from one day (a broken file must not make every story an exception)


def plan(live, today, local_hour, now):
    """The day's plan from live.json: {'level', 'why', 'note', 'updated', 'take': set, 'drop': set, 'when': {id: day}}."""
    live = live if isinstance(live, dict) else {}
    days = live.get('days') if isinstance(live.get('days'), dict) else {}
    take, drop, when = set(), set(), {}
    for day in sorted(k for k in days if isinstance(k, str)):   # oldest first: a newer day's decision on an id wins
        entry = days[day]
        if not isinstance(entry, dict):
            continue
        for f, mine, other in (('take', take, drop), ('drop', drop, take)):   # on one day drop wins
            for x in (entry.get(f) or [])[:MAX_IDS]:
                if isinstance(x, str):
                    other.discard(x)
                    mine.add(x)
                    when[x] = day
    entry = days.get(today) if isinstance(days.get(today), dict) else None
    why_ok = 'redaktøren'
    if not entry and local_hour < 6:   # the night: the evening's level holds until the editor's first update of the day
        try:
            entry = days.get((date.fromisoformat(today) - timedelta(days=1)).isoformat())
            entry = entry if isinstance(entry, dict) else None
            why_ok = 'i går'
        except ValueError:
            entry = None
    updated = None
    try:
        updated = datetime.fromisoformat(live['updated']) if live.get('updated') else None
    except (TypeError, ValueError):
        pass
    level, why = DEFAULT, why_ok
    if not live:
        why = 'ingen live.json'
    elif not entry:
        why = 'ingen plan for i dag'
    elif entry.get('level') not in LEVELS:
        why = 'ukendt niveau'
    elif 6 <= local_hour and (updated is None or now - updated > STALE):
        why = 'forældet'
    else:
        level = entry['level']
    return {'level': level, 'why': why, 'note': (entry or {}).get('note'), 'updated': live.get('updated'),
            'take': take, 'drop': drop, 'when': when}


def decision(the_plan, ids):
    """'take', 'drop' or None for a story known by these ids: the newest day's decision on any of them wins (a card's
    lead changes, so two days may name one story by two ids); on one day drop wins."""
    take, drop, when = the_plan.get('take') or set(), the_plan.get('drop') or set(), the_plan.get('when') or {}
    t, d = ids & take, ids & drop
    if not t or not d:
        return 'take' if t else 'drop' if d else None
    return 'take' if max(when.get(x, '') for x in t) > max(when.get(x, '') for x in d) else 'drop'


def in_app(story, the_plan):
    """Whether app.json carries the story: admitted to Live now, or a big story (also one older than Live's 48 hours)
    the editor has not dropped – drop wins over everything."""
    return bool(story.get('live')) or (bool(story.get('big'))
                                       and decision(the_plan, {story['id'], *(story.get('members') or [])}) != 'drop')


def admit(pool, levels, margin, the_plan, record, now, when, protect, window=timedelta(hours=24), keep=timedelta(hours=48)):
    """Which stories of the pool Live shows. pool: the leads (dicts with id, members, rank); when(story) -> datetime;
    protect(story) -> a reason or None; record: {member id: iso} of earlier admissions. Returns ({lead id: why}, the
    new record, a summary for data.json). why is one of take, big, wide, dk (protected), rank, kept (admitted earlier and
    still within the margin)."""
    floor, count = levels[the_plan['level']]
    ids = lambda st: set(st.get('members') or []) | {st['id']}
    seeded = bool(record)
    out, n_day, last = {}, {}, {}

    gone = set()   # members of stories of the day Live does not show (now): forgotten, so they never come back later

    def decide(stories, bucket):
        n, line = 0, floor
        for st in sorted(stories, key=lambda st: -st['rank']):
            mine = ids(st)
            said = decision(the_plan, mine)
            if said == 'drop':
                continue
            was = bool(mine & record.keys())
            why = 'take' if said == 'take' else protect(st)
            fresh = bucket == 'day' or not seeded   # the first pass ever decides the day before as well
            if not why and fresh and st['rank'] >= floor:
                if n < count:
                    why = 'rank'
                    line = st['rank']
                elif bucket == 'day':
                    last['capped'] = True
            # admitted earlier: stays while its rank is within the margin of the line (the floor, or the last story the
            # count let in), so Live does not flicker; older than the window: nothing new comes in, nothing goes
            if not why and was and (bucket != 'day' or st['rank'] >= max(floor, line) - margin):
                why = 'kept'
            if why:
                out[st['id']] = why
                n += 1
            elif bucket == 'day':
                gone.update(mine)
        n_day[bucket] = n
        if bucket == 'day':
            last['rank'] = line

    recent = [st for st in pool if now - when(st) <= window]
    older = [st for st in pool if window < now - when(st) <= keep]
    decide(recent, 'day')
    decide(older, 'older')
    new_record = {k: v for k, v in record.items()
                  if k not in gone and datetime.fromisoformat(v) >= now - keep - window}
    for st in pool:
        mine = ids(st)
        if st['id'] in out:
            for k in mine:
                new_record.setdefault(k, now.isoformat())
        elif decision(the_plan, mine) == 'drop':
            for k in mine:
                new_record.pop(k, None)
    why_count = {}
    for st in recent:
        if st['id'] in out:
            why_count[out[st['id']]] = why_count.get(out[st['id']], 0) + 1
    summary = {'level': the_plan['level'], 'why': the_plan['why'], 'note': the_plan.get('note'),
               'plan_updated': the_plan.get('updated'), 'floor': floor, 'count': count, 'margin': margin,
               'line': last.get('rank', floor) if last.get('capped') else floor, 'n_24h': n_day.get('day', 0), 'n_48h': len(out),
               'by_why_24h': why_count, 'candidates_24h': len(recent),
               'take': sorted(the_plan.get('take') or ()), 'drop': sorted(the_plan.get('drop') or ())}
    return out, new_record, summary
