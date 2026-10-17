# Notes – round 2, the editor: informative headlines, the day's level, the front page it composes

Part of the hjerne build, round 2 (2026-10-17). The owner's rules: docs/hjerne/notes-owner-headlines.md,
notes-owner-volume.md (revised), notes-owner-front.md. The editor is still fired by `editor.py gate` (plain Python after
each radar pass, at most `editor_fires_per_day`) – the owner approved it ("god idé med at kalde Claude").

## What was built

**Headlines (`scripts/editor.py`, `scripts/voice.py`).**

- Every story Live shows gets the editor's headline – Danish outlets too, not only the eight strongest foreign ones.
  The input's old 'Danish headlines to check' is now **'Headlines to write'**: the admitted stories without the
  editor's headline, big ones first, then by rank, at most `MAX_TITLES` = 30 a run (the rest counted: 'Headlines to
  write – 30 of 94'). Each shows the outlet and language, how long it has waited, the outlet's headline (with the
  machine's Danish for a foreign one), its teaser (≤ 200 characters) and three other outlets' headlines; a story the
  input listed above already shows only its headline. The instructions name the owner's examples ('Se billederne: Kaos
  i lufthavnen' → 'Houthi-angreb lukker King Khalid-lufthavnen i Riyadh; 12 dræbt').
- `voice.curiosity(text)` / `voice.check_headline(text, where, problems)`: a question; 'Derfor', 'Se', 'Her er', 'Her
  får du', 'Sådan', 'Det skal du vide', 'Hvorfor', 'Hvordan' at the start or after a colon or dash; 'Hvad', 'Hvem',
  'Dette er', 'Det betyder', 'Så mange', 'Læs' … at the start only (after a colon they open a quoted statement as often:
  'Kreml: Dette er en provokation' passes); '– og det er ikke godt', 'eksperter undrer sig', 'du skal vide' anywhere; a
  colon or '…' at the end; a label before a colon ('Video:', 'Chok:'); English equivalents ('Why', "Here's", 'What we
  know' …; capitalised, so 'WHO advarer' passes). 'Who: what' passes. `check_headline` adds the voice check and the
  reality check (text inside »…« left out: the source's own framing). Publish runs it on every title, on a `top`
  block's title, every block title and every `linje`; a title for a story of the movement's or a government's channel
  also gets the movement's checks.
- A title may name a story by its id or any member; it is filed in summaries.json `titles` under the card's id **with
  the card's other `members`**, so it still matches after the card's lead changes, and an earlier headline of the same
  story under another lead is replaced (one headline a story).

**The day's level (`live.json` on the digest branch).** The update may set `level` (få / normal / mange), `take`,
`drop` (story ids, by id or member; stored as the card's id) and `note` (one line, ≤ 160 characters, voice and
reality checked). Take and drop add to what earlier updates set today; a story taken in is removed from drop and back.
Publish writes live.json at **every** update (so its `updated` never goes stale for the radar's two-hour fallback),
with today's and yesterday's Danish days:

```json
{"updated": "<iso>", "days": {"2026-10-17": {"level": "mange", "take": ["<id>"], "drop": ["<id>"],
                                             "note": "Mange angreb og to topmøder.", "at": "<iso of the last change>"}}}
```

A day the editor set nothing for is absent (the radar's default `normal`). The input's **'Live – how much the app
shows today'** shows today's level and note, take and drop, how many stories of the last 24 hours are in, the radar's
line (rank, the level's floor, its soft count, and the level the radar actually applies with its why, e.g. 'forældet'),
the six weakest admitted stories (never a big, taken or protected one) and the six strongest left out.

**The front page (`front.json` on the digest branch).** The update may send `front` {lede?, blocks}; publish
validates and writes:

```json
{"updated": "<iso>", "lede": "<the update's lede>", "blocks": [
  {"kind": "top", "story": "<card id>", "title": "<headline>", "with": ["<id>"], "timeline": "<topic as the recap names it>", "picture": true},
  {"kind": "liste", "title": "Danmark", "stories": ["<id>"], "style": "kompakt"},
  {"kind": "udvikling", "topics": ["<topic>"]},
  {"kind": "citat", "quote": "q1", "who": "…", "text": "…", "link": "…", "sec": "world"},
  {"kind": "svar", "nr": "30555"},
  {"kind": "live", "n": 3},
  {"kind": "linje", "text": "14 nye angreb på Riyadh i dag"}]}
```

- Refused: an unknown kind; more than 8 blocks; more than two `top`; an unknown story; a story in two blocks (a top's
  `with` included); a story not in Live today unless it is big or taken in this update (only once the radar draws the
  line); a `liste` without a title or with more than 8 stories; a block title over 40 characters, like a day marker
  ('I dag', a weekday, a date) or a curiosity phrase; a recap topic that does not exist (any day of the archive or this
  update; stored as the recap writes it); a quote outside q1-qN; an answer number neither the static layer, answers.json
  nor the radar's fetched list holds; `live.n` outside 1-10; a `linje` over 120 characters, curious or with a reading
  word; a `front.lede` that differs from the update's `lede` (give the lede once; `front.lede` alone becomes the
  update's lede).
- Ids are stored as the card's current id (a member resolves to its card).
- Quotes in digest.json `editor.quotes` now carry `id` q1, q2 … (their order); a `citat` block carries the quote itself
  as well, so the app needs no lookup.
- Left out (or "keep"): the composition on the branch stays, re-dated and with the lede of this update, its stories that
  left the radar dropped (a `top` without its story or an empty `liste` goes). One of an earlier Danish day is not kept
  after 06: no front.json is written and the app's fixed page shows until the editor composes one (publish prints a
  note). A file of an earlier publish that this one does not write is deleted from the out folder, so `--push` never
  sends it again.
- The input's **'The front page – your composition'** shows the composition now (each block with its stories'
  headlines), the quotes q1… a `citat` may name, the palette and a short guide to the owner's taste (compact,
  overskuelighed før fuldstændighed, few kinds of information per row, block titles never like a day marker, Danish
  politics never buried; the rest is the editor's own taste and the brain). The check prints the composition in one
  line ('Composition (17.10 09.10): top, liste 'Danmark', udvikling, live', marked when older than 6 hours).

**The look (`check`/`gate`).** A line on Live ('Live: level mange (set by the editor) · 47 admitted in 24 h · the
radar's line: rank 96 · 9 wait for a headline (longest 52 min)'). New reasons, once the radar draws the line:
`8 historier i Live venter på redaktørens overskrift` (≥ 8 waiting; key `heads:<last update>`, once an update) and
`en historie i Live har ventet … på redaktørens overskrift` (one waiting > 45 minutes, 06-24 only; key
`late:<its first article>`). The wait counts from the radar's admission (`admitted.json` on the data branch: member id
→ first admitted), else the card's `found`. Both are ordinary reasons under the ceiling and the day's spread.

**The routine prompt** (docs/hjerne/routine-prompt.md): headlines for every story listed, the curiosity rule with the
owner's examples, the level with take/drop/note, the front page by its own taste with the palette's rules, the two new
files, the finishing line. **cadence.md**: the headline reasons and what round 2 adds to a run (input 37,000 → 53,000
characters on 17 October's data before the radar's line, about 4,800 tokens more a run; with the line in place a
quarter-hour's update has 5-15 stories to head).

**Tests:** tests/test_editor.py (updated: quotes' ids, 'Headlines to write' with a Danish story, a title filed with its
members and matched after the lead changed, 13 curiosity headlines refused and 8 informative ones passed, push keeps
the branch's other files with live.json and front.json written) and tests/test_editor_r2.py (15: level/take/drop and
two days, live.json at every update, a bad level/note refused, the input's line with the radar's fields, the 8 and
45-minute reasons by day only, the gate's once-an-update key, nothing before the radar's line, a full valid
composition, every refusal, a story outside Live, a kept and a stale composition, the front's lede, the input's and the
check's composition). `py -m pytest -q tests` passes for these files.

## The interface with the radar and the app (coordinate)

- **Read from the radar (data branch):** `app.json` `items` (ids, optionally members) = the admitted stories;
  data.json items' `live` (the radar's why, or null) when app.json is missing; data.json's top-level `live` (`level`,
  `why`, `line`, `floor`, `count`, `n_24h`) for the line; `admitted.json` for the wait. All read by name from the
  radar's round-2 work in this worktree (src/radar/level.py, run.py); without any of them the editor falls back
  quietly (all stories of 48 hours, no headline reasons).
- **For the app:** summaries.json `titles[id]` = {title, at, members?} – match a story by its id **or any of its
  members** (the radar's app.json carries `members`); front.json as above (blocks in order; `citat` inline; `top.title`
  is the editor's headline for that story on the front page); `editor.quotes[].id`.
- The radar has its own curiosity test (src/radar/headlines.py `curious`, to choose which outlet leads a story); the
  editor's (voice.py) checks the editor's own text and is a little different by purpose ('Hvad'/'Hvem' only at the
  start, 'Who:' lines pass, a quotation without a speaker is not refused). Unifying them is possible later.

## Open

- The level's sizes in the input (about 25 / 45 / 80) are the owner's first guess; the radar's `live_levels` in
  config/settings.json govern – tune both together on real data (scripts/rank_check.py).
- On the first runs after the launch the queue of stories without a headline is large (about 90 on 17 October's data);
  30 a run clears it in three or four updates.
