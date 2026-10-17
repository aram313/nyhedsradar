# The editor's cadence: a look every quarter of an hour, Claude when it is needed

The owner (2026-10-17): "Claude skal køre hvert 15. minut på siden og vurdere, om der er noget, der skal tilrettes.
Der er tokens nok."

## Why not four routines every hour

The first design ran four Claude Code routines (cron at minutes 0, 15, 30 and 45): 96 runs a day. The review of
2026-10-17 found that routines have a **daily run cap per account** (third-party guides report about 15 runs a day on
Max and 5 on Pro; the routine API itself speaks of "a fire cap or a 429 on run"). Runs past the cap are refused, or
billed at API rates when extra usage is on. Today's twelve editor runs plus the caretaker are 13 a day, under the
reported 15; 96 would stop after about two hours of the day. The real cap could not be read from here: **the owner
reads it at claude.ai/code/routines (or `/usage`)** and sets `editor_fires_per_day` to fit under it (with the
caretaker's one run a day).

## The design: the look is Python, Claude is fired when the look says so

- **The look** is `scripts/editor.py gate`: plain Python, no tokens. It runs in GitHub Actions as a step after every
  radar pass (`radar.yml`, "Editor's quarter-hour look"; the radar runs every 5 minutes, so the look is at least every
  quarter of an hour). It computes exactly what `editor.py check` prints and its verdict.
- **The fire.** When the verdict says OPDATÉR and its reason holds, the gate fires the editor's routine through the
  routine's **API trigger** (`ROUTINE_FIRE_URL` and `ROUTINE_FIRE_TOKEN`, GitHub secrets made from the routine's API
  trigger at claude.ai/code/routines; the text sent is the look's reason). Without the two secrets the step only looks
  (a dry run, printed in the Actions log), so nothing changes until the owner adds them.
- **The record.** Every fire (and every refused or dry fire) is kept for three days in `state/editor-gate.json` on the
  data branch: when, why, the reason keys and the result.
- **The routine** is one routine with the prompt of [routine-prompt.md](routine-prompt.md) (the private weighing guide
  inserted at `[WEIGHING-GUIDE]`) and no schedule of its own – or the existing twelve-a-day routine
  (`trig_01B5p6DmEx8pz9cDLZzwxbHj`) with the new prompt, its schedule removed and the API trigger added. It still runs
  `editor.py check` first and may stop with one line when the reason is covered.

## The gate's rules (`editor.gate_decision`)

| Rule | Why |
|---|---|
| A reason fires once. Each reason has a key: a big story or a tier 1-3 story by its **first article's id** (a card's id is its lead's, which changes as outlets join), a new answer by its number, the morning and the evening by the day, the two-hour reason by the update it is about, a stopped radar by its last pass. | An OPDATÉR the routine judged covered never comes back every quarter of an hour. |
| No fire while an update is under way: fired less than 30 minutes ago and no update published since. | Two runs never start the same update. |
| At most one fire a quarter of an hour. | The look's own rhythm. |
| At most `editor_fires_per_day` fires a Danish day (config/settings.json, **12**); two of them are kept for the morning's front page (first run after 06) and the evening's notification (first update after 21). | The run cap. |
| The day's fires are spread over 06-24: by each hour at most its share of the ceiling, and one more. | A busy morning does not use up the afternoon. |
| Between 00 and 06 only a big story (or a stopped radar) fires, and only once a night. | The morning run takes the rest. |

The verdict itself (`editor.verdict`, also what `check` prints) was tightened at the same time:

- a story is new only when its **first article** came after the last update (the review found a Houthi story found at
  20.35 counted as new at 02.20 and again at 09.10 because its card changed lead at 23.55);
- a story that is already a pick or in the recap calls for no update of its own (the check marks it `= pick 3` or
  `= in the recap`);
- a big story calls for an update only when it weighs: tiers 1-10 by the books' order, or Danish (Danish politics is
  never buried); a big story of tier 11 or 13 waits for the next update;
- the two-hour reason holds only when something changed: a story of weight or at least three new wire lines;
- a stopped radar (no pass for 30 minutes) is a reason of its own: `radaren står stille`, and the check's first line
  says when the radar last ran.

## Measured: 16 October replayed every quarter of an hour

The same replay as the first design (the day's stories, outlets and wire lines as they were at each quarter, the
look followed: every fire becomes a full update at that moment), with the new verdict and the gate:

| | updates a day | when |
|---|---|---|
| first design, every OPDATÉR followed | 28 | 23 of them for a big story |
| new verdict, no ceiling | 22 | 06.00 first, then as news of weight came; none at night |
| new verdict, ceiling 12 (the default) | 12 | 06.00, 08.00, 10.00, 10.45, 12.45, 14.00, 15.00, 15.45, 17.00, 18.45, 20.30, 21.00 |

With the ceiling of 12 the gate held back 13 looks of the afternoon and evening ("fordeles over dagen") and all 11
looks after 21.00 (the evening's update used the last fire): what happens after 21 waits for the morning. The check: 2,252 characters on average (at most 3,596, never more than 33
lines). A full input: 35,112 characters on average (27,756-46,891).

## Tokens a day, against today's twelve updates

Assumptions (not measurable here): about 3.3 characters a token; the fixed context of a run is about 17,000 tokens of
Claude Code's own instructions and tools and the routine prompt **plus the repository's CLAUDE.md, which Claude Code
loads into every session** (22,776 characters, about 7,000 tokens): about 24,000 tokens. A full update writes about
4,000 tokens.

| | runs a day | new tokens a run (fixed + input + written) | new tokens a day | against today |
|---|---|---|---|---|
| today: twelve updates at fixed times | 12 | 24,000 + 9,200 + 4,000 | about 450,000 | 1 |
| first design: four routines, 96 runs, 28 updates | 96 | stop: 24,000 + 700 + 200; update: + 10,600 + 4,000 | about 2,800,000 | about 6.3 |
| **the gate, ceiling 12** | 12 | 24,000 + 10,600 + 4,000 | about 465,000 | **about 1.0** |
| the gate, no ceiling (if the cap allows) | 22 | as above | about 850,000 | about 1.9 |

So the gate costs about what today's twelve updates cost, but the twelve now come when the news calls for them, and
the quarter-hour look costs no tokens at all. Four fifths of the first design's cost was the fixed context of runs
that stopped after the check; the gate has none of those.

## If the cap is higher

Raise `editor_fires_per_day` in config/settings.json (the gate reads it at every look); the replay's day without a
ceiling needed 22. Keep one or two runs a day free for the caretaker and for the owner's own runs.
