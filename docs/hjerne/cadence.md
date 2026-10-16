# The editor's cadence: a look every quarter of an hour

The owner (2026-10-17): "Claude skal køre hvert 15. minut på siden og vurdere, om der er noget, der skal tilrettes.
Der er tokens nok."

## The four routines

A Claude Code routine on the owner's plan fires at most once an hour, so the quarter-hour takes four routines with the
same prompt ([routine-prompt.md](routine-prompt.md) plus the owner's private weighing guide):

| Routine | Schedule (cron) | Fires at |
|---|---|---|
| editor :00 | `0 * * * *` | every hour on the hour |
| editor :15 | `15 * * * *` | every hour at a quarter past |
| editor :30 | `30 * * * *` | every hour at half past |
| editor :45 | `45 * * * *` | every hour at a quarter to |

The schedule names only minutes, so time zones and summer time do not matter. The twelve-a-day editor routine
(`trig_01B5p6DmEx8pz9cDLZzwxbHj`) is retired at launch – or becomes the :00 routine with the new prompt and the hourly
schedule. The caretaker routine is unchanged. The sandbox still has no internet; the routines need the same push right
to the `digest` branch the editor has today.

Each run starts with `editor.py check` (about 40 lines at most) and stops there with one line unless something of
weight has happened. The check says `OPDATÉR` when, since the last full update:

- a big story came, or one grew big (the radar's `big`; outlets that joined after the update count, from items.json);
- a story of tier 1-3 (the books' order: the leading state with another power, the leading state's acts, a great
  power's acts) reached two outlets;
- Hizb ut-Tahrir has a new answer the radar fetched after the last update;
- between 06 and 24 Danish time, two hours have passed;
- it is the first run after 06 (the day's own front page);
- it is the first run after 21 with no update since 21 (the phones' one notification a day goes with that update).

Claude reads the list and judges: the verdict is a recommendation, not an order (routine-prompt.md, step 2).

Two runs can overlap when a full update takes longer than a quarter of an hour. `publish --push` fetches the digest
branch first and refuses when another update landed after its input ("run input again"), so two updates never
overwrite each other; every other file on the digest branch is carried over unchanged.

## What a run costs – measured on today's data

Measured with the live data and digest branches of 16-17 October 2026 (`git fetch origin data digest`):

- **the check**, replayed for every quarter of 16 October (96 runs, the day's stories, outlets and wire lines as they
  were at each moment): 1,919 characters on average (median 1,913, at most 3,296), never more than 33 lines. The live
  check at 01.14 on 17 October: 2,774 characters, 27 lines.
- **a full input**:
  - in the quarter-hour rhythm, following every OPDATÉR of the replay (28 updates): 32,691 characters on average
    (27,121-40,859, median 33,538) – the window since the last update is short;
  - in today's rhythm (the twelve real update times of 16 October, the last update an hour or more before): the
    current tool 30,422 characters on average (24,647-46,762); the new tool at the same moments 38,727 – the brain
    (about 5,900) and the front page now (about 1,200) are new, the recap shows the newest five lines per topic;
  - live at 01.14 on 17 October (an hour since the last update): new 36,669, current 26,805.
- **how often the check calls for an update**: 28 of the 96 replayed runs said OPDATÉR – 23 for a big story, 2 for two
  hours without an update, 1 for the first run after 06, 1 for the evening notification, 1 for a tier-1 story with two
  outlets; 27 of them between 06 and 24, one at night (03.30).

## Tokens a day, against today's twelve updates

Assumptions (not measurable here): about 3.3 characters a token for this mix of Danish, English, Arabic wire lines and
long links; about 17,000 tokens of fixed context per run (Claude Code's own instructions and tools, and the routine
prompt with the weighing guide); a full update writes about 4,000 tokens (update.json and its reasoning), a stopped run
about 200. A stopped run takes two turns (check, one line), a full update about seven (check, input, two reads, write,
publish, one line); each turn re-reads the context so far from the cache.

| | runs a day | full updates | new tokens a run (fixed + material + written) | new tokens a day | with the cache re-reads | against today |
|---|---|---|---|---|---|---|
| today: twelve updates | 12 | 12 | 17,000 + 9,200 + 4,000 | about 360,000 | about 2,000,000 | 1 |
| every 15 min, every OPDATÉR followed | 96 | 28 | stop: 17,000 + 600 + 200; update: + 9,900 + 4,000 | about 2,100,000 | about 7,200,000 | about 3.6-5.8 |
| every 15 min, half the OPDATÉRs followed | 96 | 14 | as above | about 1,900,000 | about 5,300,000 | about 2.6-5.3 |

So the quarter-hour rhythm costs about three to six times today's twelve updates: the lower figure counts every
re-read of the cache, the higher only the new tokens. With 10,000 or 25,000 tokens of fixed context instead of 17,000,
the new-token factor is about 5.1 or 6.3. Most of the new cost is the 96 runs' fixed context (about four fifths of the
new tokens), not the news: a shorter input saves little; fewer runs save much. If twelve updates a day are about a
tenth of the owner's plan (CLAUDE.md, 2026-10-11), the quarter-hour rhythm uses roughly a quarter to a half of it.

If it is ever too much, in order of effect: at night (00-06) only the :00 routine (78 runs a day, about a fifth less);
every half hour (two routines, 48 runs, about half the cost above); a stricter verdict (for example a big story only
when its tier is 1-10).
