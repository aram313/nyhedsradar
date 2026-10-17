# Notes – the editor: the front page with the brain, every 15 minutes

Part of the hjerne build (2026-10-17). The owner's decision: the brain (the books' order of importance and the amir's
answers) is used only to select and weigh the news; the app shows no analysis by Claude or Khabar; concepts open wiki
pages compiled from the amir's answers; Claude looks at the site every 15 minutes and adjusts what needs adjusting.

## What was built

**`scripts/brain.py`** – the brain section of the editor's input, at most 6,000 characters (today 5,845):

- the purpose, said plainly: weigh the lede, the picks, Dagens historie and the order of the recap's topics by it; the
  app shows no analysis; the editor's own text stays reality, never a reading or judgement of its own and never the
  movement's reading presented as fact;
- a. the books' order of weight, tiers 1-13, from `config/method.json` (the radar part's version: tier texts, the
  leading state and the powers) with built-in texts for what the config does not word, and the weight rules V of
  `operating-card.md` compactly (weight = whether a development moves; a great power's act is never dropped; the
  campaign against the belief weighs up; Danish politics is never buried, two or three Danish picks);
- b. 'Den internationale tilstand ifølge Hizb ut-Tahrirs nyeste svar': each power of the config (today USA,
  Storbritannien, Frankrig, Rusland, Kina) with its current reading from `public/viden/movement.json`, one dated,
  attributed line each – the first sentence, cut at a clause only when longer than 260 characters;
- c. the states, groups, issues and concepts the 40 top stories name, with their current reading (the concept page's
  `lead_da` from `begreber.json`, else the layer's `current`), one dated line each, at most 12 – singles by how many
  top stories name them, then up to three relations two subjects share in two stories or more (`relations` of the
  pages, else the layer's `a--b`); lines are dropped from the end when the 6,000 would be passed (today 8 fit). Names
  match by the concept index's aliases (whole word, possessive s, case per page – the app's linker rule) together with
  the brain's own headline forms for the same ids (`iransk*`, `Kreml`, `Trump` …, which the wiki rightly does not
  link) and the radar's `actors` of the story; without the index, by the layer's subjects and those forms;
- d. the movement's three newest answers (date, number, title), the editor's noted ones included.

`tier_of()` gives a story's tier: the radar's `tier`, else `radar.method`'s weighing of the headline (so the tier is
there while old data has none), else none.

**`scripts/voice.py`** – the content rules as checks, ported from Khabar 2: `check_voice` and its regexes from
`editor2.py` exactly (violence, peoples and religions, 'Israel', forgeries), with one fix – 'til våben' is refused as a
call to arms ('Til våben!', 'grib til våben'), not in 'gjorde antisemitisme til våben' (two of the last month's
checked headlines had that); `check_reality` for the editor's own lede and summaries, narrowed to the movement's
reading vocabulary (satellit, underordnet stat, i USA's bane, den førende stat, faldet fra stormagt, mellemmagt,
marionet, vasal, aftalt spil, 'ifølge Hizb ut-Tahrir' …) – Khabar 2's list also held 'står bag', 'på vegne af', 'agent'
and 'forræderi', which the month's summaries used four times, every time as plain news; `check_movement` for an
answer's readings (no agent words; no attack with dead said to be staged unless 'gerningsbelæg mangler'; no serving
claim near a mosque, imam, scholar, media outlet, Danish person or organisation, or the non-ruling names of
build_movement; a government is read as the state, with build_movement's GOVERNMENT pattern, as the wiki part asked;
quotations at most 60 characters; no local paths). Run on the month's real output: 0 of 370 recap lines, 0 of 288
summaries and neither the current lede nor its quotes refused; 2 of 384 headlines ('martyr'); on the whole movement
layer (1,479 texts) one
flag – 'vasaller' in a reading of Japan, which a new answer would have to say as 'underordnet'.

**`scripts/editor.py`**

- `check` – at most about 40 lines (measured at most 33): the time of the last full update; what is new since – the
  stories of weight (tier 1-5, big or 3+ outlets) with tier, outlets and time, the heaviest first, and stories found
  before the update that grew across a line since (became big, reached three outlets, or a tier 1-3 story reached
  two), with '+N since' from items.json (outlets counted by distinct sources, so an outlet's second article is no new
  outlet); the number of new wire lines and the four newest in Danish; a new answer waiting; the front page now (the
  lede and when it was written, Dagens historie's topic as the app chooses it, the picks); and the verdict, `INTET NYT
  AF VÆGT` or `OPDATÉR: <why>` – a big story or a tier 1-3 story with two outlets since the last update; a new answer
  fetched after it; two hours without an update between 06 and 24; the first run after 06; and (added) the first run
  after 21 with no update since 21, so the day's one notification still goes out around 21.
- `input` – the brain first, then 'The front page now' (lede with its time, Dagens historie, the picks with tier,
  quotes and moves counted), the recap so far (the newest five lines per topic and the count of the rest), the top
  stories and the new stories with their tier, the new stories including those that grew (+N since), 15 of the owner's
  removals, summaries, headlines, wire lines, Hizb ut-Tahrir's new answer when one is waiting (the newest, its text up
  to 32,000 characters, the rules and the subject ids to use), 'How small an update can be', and the format (the
  `answer` part only when an answer waits).
- `publish` – an update may be small: `lede`, `picks` and `quotes` left out (or "keep") stay as they are on the front
  page; picks the radar dropped go; `moves` stay until the story is moved back to its own section (before, every
  update dropped the earlier moves); `lede_at` keeps the lede's own time, and a lede from an earlier Danish day is
  refused after 06. The editor's text is checked: voice for the lede, recap lines, quotes, headlines and summaries;
  reality for the lede and summaries. The `answer` object is checked (a new answer of the radar's analyses.json that
  neither movement-index.json nor answers.json holds; its own date; 'Ifølge Hizb ut-Tahrirs svar af d/m/åååå' with
  that date in note_da and in every reading; kinds stilling, forhold, plan, fremgangsmåde, rolle, tilstand, motiv;
  subject, object and begreber ids known or new lowercase-with-hyphens – a relation a--b in alphabetical order, a
  near-twin of a known id refused; the voice and movement rules) and written to `answers.json` on the digest branch in
  the shared schema exactly (`{"items": {nr: {nr, date, title_da, question_da, note_da, url, readings, begreber}}}`),
  kept forever. With `--push` it fetches the digest branch first and refuses when another update landed after the
  input (`input.meta` holds the branch's commit at input time); the push builds the new commit from every file the
  branch holds, so answers.json – or a live.json of another part – is never lost. Only the first update at or after 21
  notifies the phones (unchanged).

**Tests** (`tests/test_editor.py`, 28 tests, 16 new): the check (what is new, the verdict and its reasons, quiet at
night and at a recent update, the first run after 06, a story that grew big, at most 40 lines); the brain (the order,
the powers' dated first sentences, the named subjects and a relation, the newest answers incl. a noted one, the
concept pages' leads and aliases, the budget dropping relations first, clause cuts, attribution and date on every
line); the input carrying the brain and the front page; small updates (lede, picks, quotes and moves kept, a move
undone, quotes cleared, yesterday's lede refused after 06 and kept at night); the reality and voice rules on the
editor's text and on news vs readings; the answer object (asked with its text, noted in the exact schema, not asked
again, kept forever, not calling for an update once an update has seen it, refused for each broken rule, the
static answers never asked, 'gerningsbelæg mangler' allowed); the push carrying the other files of the digest branch
(a real git repo); publish refusing after another update landed. `py -m pytest -q tests`: 114 passed, 5 skipped
(the five need cryptography or Pillow, not installed locally).

**Docs:** `docs/hjerne/routine-prompt.md` (the new routine prompt, public parts, `[WEIGHING-GUIDE]` where the owner's
guide goes) and `docs/hjerne/cadence.md` (four routines at minutes 0, 15, 30 and 45; the measured sizes and the token
estimate).

## Measured (16-17 October, `git fetch origin data digest`, the live files)

- The check: 1,919 characters on average over the 96 quarters of 16 October replayed (max 3,296; at most 33 lines);
  live at 01.14 on 17 October 2,774 characters.
- A full input: 32,691 characters on average in the quarter-hour rhythm (28 updates when every OPDATÉR is followed);
  the current tool 30,422 and the new one 38,727 at today's twelve update times; live at 01.14, new 36,669 and current
  26,805. The brain adds about 5,900 and the front page about 1,200; the recap's five-lines-per-topic takes some back.
- The verdict on 16 October: 28 of 96 OPDATÉR (23 big stories, 2 two-hour, 1 first after 06, 1 evening, 1 tier 1);
  27 between 06 and 24.
- Tokens: about three to six times today's twelve updates (cadence.md) – about four fifths of it the 96 runs' fixed
  context, so fewer runs save much more than a shorter input.

The replay scripts were scratch work (not committed): each quarter's state was rebuilt from the live files – stories
and outlets as found by then (items.json), wire lines published by then, the recap's lines by the last update.

## For the consolidation (CLAUDE.md, README, CHANGELOG – not edited here)

- CLAUDE.md 'Scheduling and Claude routines': the editor is four routines every 15 minutes with `editor.py check`
  first (cadence.md), replacing the twelve-a-day `trig_01B5p6DmEx8pz9cDLZzwxbHj`; the weighing guide stays private;
  `scripts/editor.py` in Architecture: check / input / publish, brain.py, voice.py, answers.json on the digest branch.
- At launch the owner sets up the four routines (same prompt, the weighing guide added) and retires the old one.
- `digest.json`'s editor notes have a new field `lede_at` (the app may ignore it); `answers.json` is a new file on the
  digest branch (public, like the rest) that the app's wiki should read for answers after the static 321 – the wiki
  part notes that the build does not merge it.
- The owner's notes of the same day that touch the editor were not part of this brief and are not built here:
  `notes-owner-headlines.md` (an informative headline for every story the app shows, Danish ones too – more `titles`
  per update than the eight today) and `notes-owner-volume.md` (`live.json` on the digest branch with take/drop, and a
  check that says OPDATÉR when candidates wait). Both change editor.py's input, publish and check; the push already
  keeps any other file on the digest branch. Note for the volume rule: if every new candidate needs a decision, nearly
  every quarter becomes a full update – the cost then is that of 96 full updates a day, about 8 times today.
- summaries.json grows with more updates (today 288 summaries and 384 headlines, 153 KB, over four days; with 28
  updates a day up to about twice that) – relevant to the performance work.

## Review fix (2026-10-17): the look in Actions, Claude when it is needed

The four-routines design is replaced (routines have a daily run cap): `editor.py gate` runs after every radar pass and
fires the routine through its API trigger, once per reason, at most `editor_fires_per_day` a day. The verdict counts a
story as new only when its first article is, leaves picks and recap stories out, waits with big stories of tier 11 and
13 (not Danish ones), needs a change for the two-hour reason and names a stopped radar. Brain lines prefer a newer
filed reading; all of the editor's own text is checked. Replay, rules and tokens: [cadence.md](cadence.md).
