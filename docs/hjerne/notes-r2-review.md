# Round 2 – the reviewers' findings fixed (2026-10-17)

The two reviews of round 2 (logic, ux-speed) gave 21 findings: 3 high, 9 medium, 9 low. Every high and medium one is
fixed; of the low ones, all but two are fixed (below). Tests: 222 passed, 5 skipped (`py -m pytest -q tests`); `node
--check` clean for app.js and sw.js; phone shots at 430 px, 2x, light and dark, text size 1 and 1.3, on the 08:20 data
of 17/10 (public/dev/r2), no console errors. App version `?v=20261017t`.

## High

1. **The editor's level lapsed every evening** (logic). `src/radar/level.py` held få/mange only 2 hours after the last
   publish, shorter than the gaps the gate leaves between updates (1 h 45 – 2 h on a busy day, longer on a quiet one),
   so a quiet day was padded and a heavy day shrank. Now:
   - `STALE` is 6 hours (the front page's own limit), counted from live.json's `updated`, which every publish writes;
   - between 00 and 06 the evening's level holds until the editor's first update of the new day (`why: 'i går'`)
     instead of falling to normal at midnight;
   - the gate has a new reason when today's level is not normal and live.json is 5 h 15 min old: `dagens niveau (få)
     holder kun 6 timer efter sidste opdatering` (key `level:<live.json's time>`);
   - the input's sentence now says what is true (applied at the next pass, held for the day as long as the editor
     publishes every six hours).
   - Test: få held three hours without an update admits exactly what it admitted (`test_level.py`).
   Not done: excluding stories admitted under a fallback from 'kept'. With the longer hold and the night rule the
   fallback now happens only when the editor has really stopped for six hours, and then Live should show normal.
2. **A dropped big story stayed in app.json** (logic). app.json now carries a story when it is admitted, or big and not
   dropped (`level.in_app`): drop wins over everything, as designed. The editor's `admitted()` also leaves out what
   live.json drops, so a dropped story is out of 'Headlines to write' and the count at once, before the radar's next
   pass.
3. **A lead change looked like a new story in the app** (ux-speed). The app now carries a card over when its lead
   changes (`carryOver` in `stories()`): when a card's id is new but one of its members was an earlier card's, the
   earlier card's opened state, its open 'Andre medier', 'seen' (no glow, not counted in 'n nye historier'), 'delt' and
   first-found time (the unread dot) pass to the new id, and its rows are renamed in place, so the page patch keeps the
   very element and its picture. Checked in the browser: a story opened in Live, its id swapped to a member, a reload –
   the same element, still open, no glow, no pill.

## Medium

4. **The app without app.json showed the whole pool** – now it keeps the stories data.json marks `live` and the big ones
   not in `live.drop` (`slim()`); before round 2's radar (no `live` in the file) everything as before. Checked: 87
   stories from data.json, as app.json.
5. **Yesterday's drop overrode today's take** – `level.plan` resolves take and drop by day, oldest first (a newer day's
   decision on an id wins; on one day drop wins), and `level.decision` resolves a story by all its ids with the newest
   day winning, so a take today by the lead's id undoes yesterday's drop by a member's. The input shows yesterday's
   decisions still in force ('Still in force from yesterday: …'), and 'Just below the line' no longer offers a story
   the editor dropped. The prompt says both hold today and tomorrow, the newest decision winning.
6. **Round 1's curiosity headlines counted as written** – a filed headline that fails `voice.check_headline` covers no
   story (`good_title`): it is listed under 'Headlines to write' again, and every publish removes such stored headlines
   from summaries.json (on the 17/10 file: 44 of 374 – questions, 'Analyse: …', 'Sådan …', 'Hvorfor …', '– video', the
   op-ed thesis, and 'Besættelsesstyrker …' without Israel's name). The app also skips an editor headline its own
   curiosity test flags, until the editor writes it anew.
7. **Channel words passed the voice check** – outside a quotation `check_voice` now refuses the channels' names for
   Israel ('den zionistiske fjende', 'Zionist-regimet', 'zionistiske bosættere/styrker', 'zionisterne'), 'heroisk', and
   'helte' near fighting. 'Besættelsesstyrker' and the like are refused in Israel's place but allowed beside Israel's
   name – the owner's headline rule keeps the source's loaded words ('Israelske besættelsesfly'), the content rule
   wants Israel named. The ideology named as an idea ('zionismen') stays allowed. 'Dette sker …', 'Det her sker …' open
   a curiosity headline. These checks run on everything the editor writes (titles, lede, lines, quotes, summaries, the
   front page). Tests with QudsN-style headlines in `test_editor_r2.py`.
8. **The main story twice on the front page** – the Live strip skips every story another block shows or names (also a
   later block), in the composed page and in the fixed one (the lead and Døgnets vigtigste).
9. **Large text cut the editor's headlines** – the hero's three-line clamp now wins (`.story.hero:not(.open) .hero-tx
   .h`), and at text size 1.15 and up closed rows with a picture show three headline lines in the same row height (class
   `ts-l` on #list; the meta line 4 px closer). The Live ticker keeps two lines: its rows are shorter and full width
   (three lines there overflowed the row – seen in the first shot and changed).
10. **Pictures fetched again at every reload** – a failed picture is remembered (`badPics`) and never put back by the
    page patch: a thumbnail falls back to the initials, the hero to our small copy, then to no picture. A picture the
    observer let load is drawn without `loading="lazy"` afterwards (`nearPics`), so those rows no longer differ at
    every reload.
11. **Judgements and '– video' in headlines** – `check_headline` refuses 'egentlige', 'reelle', 'i virkeligheden',
    'vejer tungere', 'i realiteten' and the like unless the headline is someone's statement ('Who: what', a who of at
    most five words before the colon), and a trailing '– video', '– se', '(video)', '– billeder'.

## Low

12. **The 45-minute reason was keyed to one story** – every story that has waited too long gets its own `late:` key, so
    a later one fires even when the oldest stays unheaded.
13. **The 15-minute expectation** – not a code change: cadence.md and launch.md say plainly that with 12 fires a day a
    story waits up to about two hours for its headline, and none comes after the day's last fire; raise
    `editor_fires_per_day` as the run cap allows.
14. **Dropped stories offered back** – fixed with 5.
15. **Old compositions at night** – the app takes a composition at night only when it is at most 12 hours old; a kept
    composition loses its `linje` blocks when the Danish date has changed (a line of '… i dag' is not tomorrow's).
16. **A headline from another outlet's angle** – the input and the prompt say the headline states the news of the
    outlet's article listed first, the one 'Læs' opens. (Storing which member a headline was written for: declined –
    the instruction is enough, and Læs opening another outlet than the card names would confuse more.)
17. **Curiosity headline with no teaser** – the app uses another outlet's plain headline (Danish first, else English),
    with that outlet's name and link; 'Headlines to write' lists big stories first, then the stories the app shows
    worst (a curiosity headline, or only the machine's Danish), then by rank. 'Kan Europa stole på USA? Mette
    Frederiksen tøver' stays until the editor writes it: one article, no teaser, nothing to stand in.
18. **Redraws under the finger** – `staleOn` goes through `renderSoon` (which now merges the options of calls that wait),
    and `redrawPages` waits while a finger is on the screen or the page still moves.
19. **No 'Dagens historie' when the first main story left** – the heading follows the first main block actually drawn;
    when none is left, the day's main story leads.
20. **The meta line cut mid-word** – the outlet's name shrinks with an ellipsis; the time and 'ubekræftet' stay whole.
21. **Teaser cut mid-clause** – a teaser too long for a headline ends at its main clause, before ', hvilket …', ', som …'
    and the like (after 50 characters), where it has one.

Declined beyond the above: storing a headline's member (16), excluding fallback admissions from 'kept' (1).

## Files

`src/radar/level.py`, `src/radar/run.py`, `scripts/editor.py`, `scripts/voice.py`, `public/app.js`,
`public/style.css`, `public/index.html` (`?v=20261017t`), `docs/hjerne/routine-prompt.md`, `docs/hjerne/cadence.md`;
tests in `tests/test_level.py`, `tests/test_editor.py`, `tests/test_editor_r2.py`, `tests/test_app_speed.py`.
