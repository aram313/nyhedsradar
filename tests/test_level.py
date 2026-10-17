"""Live's level (src/radar/level.py): the editor's plan, the rank floor and the soft count, take and drop, the stories
that are never cut, and what earlier passes admitted."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import level  # noqa: E402

NOW = datetime(2026, 10, 17, 10, 0, tzinfo=timezone.utc)
LEVELS = {'få': (104, 3), 'normal': (96, 5), 'mange': (88, 8)}


def plan(lvl='normal', take=(), drop=(), age=timedelta(minutes=10), today='2026-10-17'):
    return level.plan({'updated': (NOW - age).isoformat(),
                       'days': {today: {'level': lvl, 'take': list(take), 'drop': list(drop), 'note': 'en travl dag'}}},
                      '2026-10-17', 12, NOW)


def pool(n=12, top=120, step=3, hours=1):
    return [{'id': f's{k}', 'members': [f's{k}', f'm{k}'], 'rank': top - step * k,
             'published': (NOW - timedelta(hours=hours)).isoformat()} for k in range(n)]


def admit(stories, the_plan, record=None, protect=lambda st: None):
    return level.admit(stories, LEVELS, 6, the_plan, record or {}, NOW,
                       lambda st: datetime.fromisoformat(st['published']), protect)


def test_plan_falls_back_to_normal():
    assert level.plan({}, '2026-10-17', 12, NOW)['level'] == 'normal'
    assert plan('mange')['level'] == 'mange' and plan('mange')['note'] == 'en travl dag'
    assert plan('mange', today='2026-10-16')['level'] == 'normal'        # no plan for today yet
    assert plan('mange', age=timedelta(hours=3))['level'] == 'normal'   # stale in the daytime
    night = level.plan({'updated': (NOW - timedelta(hours=5)).isoformat(), 'days': {'2026-10-17': {'level': 'få'}}},
                       '2026-10-17', 3, NOW)
    assert night['level'] == 'få'   # the editor sleeps at night: the evening's level holds
    assert plan('meget')['level'] == 'normal'
    stale = plan('mange', take=['a'], drop=['b'], age=timedelta(hours=3))
    assert stale['take'] == {'a'} and stale['drop'] == {'b'}   # single stories still follow the editor


def test_floor_and_soft_count():
    on, record, info = admit(pool(), plan('normal'))
    # normal: at most 5 above the floor 96 (ranks 120, 117, … – 12 of them reach 96)
    assert sorted(on) == ['s0', 's1', 's2', 's3', 's4'] and set(on.values()) == {'rank'}
    assert info['n_24h'] == 5 and info['line'] == 108 and info['floor'] == 96
    assert set(record) == {f'{p}{k}' for p in 'sm' for k in range(5)}
    few, _, _ = admit(pool(), plan('få'))
    assert sorted(few) == ['s0', 's1', 's2']
    many, _, info = admit(pool(), plan('mange'))
    assert len(many) == 8
    # a quiet day is never padded: nothing below the floor comes in
    quiet, _, info = admit(pool(top=99), plan('mange'))
    assert sorted(quiet) == ['s0', 's1', 's2', 's3'] and info['line'] == 88


def test_once_admitted_stays_while_near_the_line():
    _, record, _ = admit(pool(), plan('normal'))   # s0–s4 (ranks 120 … 108) are in Live
    stronger = [{'id': f'n{k}', 'members': [f'n{k}'], 'rank': 125 - k, 'published': NOW.isoformat()} for k in range(5)]
    on, record2, info = admit(stronger + pool(), plan('normal'), record)
    assert all(on.get(f'n{k}') == 'rank' for k in range(5))   # the strong new stories come in at once …
    # … and what Live showed stays while it is within the margin (6) of the new line (121): a soft count
    assert [on.get(f's{k}') for k in range(5)] == ['kept', 'kept', None, None, None]
    assert info['n_24h'] == 7 and info['line'] == 121
    assert 'm2' not in record2 and 'm4' not in record2 and 'm1' in record2   # what left Live is forgotten: it never comes back after 24 h
    # by a member's id too: the story's lead changed, its members did not
    moved = [{**st, 'id': 'x' + st['id']} for st in pool()]
    on, _, _ = admit(stronger + moved, plan('normal'), record)
    assert on.get('xs0') == 'kept'


def test_take_drop_and_protected():
    stories = pool()
    on, record, info = admit(stories, plan('normal', take=['m9'], drop=['s0']),
                             protect=lambda st: 'big' if st['id'] == 's11' else None)
    assert on['s9'] == 'take' and on['s11'] == 'big' and 's0' not in on
    assert 's0' not in record and 'm0' not in record
    # drop wins over everything, even a big story
    on, _, _ = admit(stories, plan('normal', drop=['m11']), protect=lambda st: 'big' if st['id'] == 's11' else None)
    assert 's11' not in on
    assert info['take'] == ['m9'] and info['drop'] == ['s0']


def test_older_stories_keep_their_admission():
    old = pool(hours=30)
    on, _, _ = admit(old, plan('normal'))   # the first pass ever: the day before is decided as well
    assert len(on) == 5
    _, record, _ = admit(pool(hours=2), plan('normal'))
    on, _, info = admit(pool(hours=30), plan('normal'), record)
    assert len(on) == 5 and set(on.values()) == {'kept'} and info['n_24h'] == 0
    on, _, _ = admit(pool(hours=30), plan('normal'), {'other': NOW.isoformat()})
    assert on == {}   # nothing new comes in after 24 hours
    on, _, _ = admit(pool(hours=60), plan('normal'), record)
    assert on == {}   # beyond the app's 48 hours
