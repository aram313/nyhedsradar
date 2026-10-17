# Round 2 – speed and smoothness (2026-10-17)

The owner's rule: docs/hjerne/notes-owner-performance.md ("Det skal føles smooth"). Files: `public/app.js`,
`public/style.css`, `public/sw.js`, `public/index.html` (`?v=20261017s`), and a new test file `tests/test_app_speed.py`.
I left CHANGELOG, CLAUDE.md and README alone, as this round's instructions say.

## How it was measured

- **Browser.** Headless Edge 155, driven through the DevTools protocol by a small Node script that uses Node's built-in
  WebSocket. Nothing was installed.
- **Phone profile.** A 390 × 844 mobile viewport at 3x with touch. The CPU was slowed **5×**
  (`Emulation.setCPUThrottlingRate`).
- **What was recorded.** Long tasks and layout shifts through an injected `PerformanceObserver`, and every frame through
  a `requestAnimationFrame` recorder.
- **Inputs.** Real touch events for pull-to-refresh, and `Input.synthesizeScrollGesture` for scrolling.
- **Data.** The round-2 preview set (`public/dev/r2`: the radar's app.json of 17/10 09:05 with 87 stories, and the
  editor's front.json, digest, summaries and moves). It was served by a small local server. For each reload, the server
  can make app.json look like a new radar pass: a new `updated` time and two new stories at the top.
- **Before/after.** "Before" is a copy of `public/` at commit 0849065. "After" is this change. Each was run three times
  in a fresh browser profile; the numbers below are medians.

The scripts (measure.js, profile.js, trace.js, smoke.js, server.js) are in the session scratchpad, not in the repository.

A "long task" blocks the page for more than 50 ms. "Blocking time" is the part of all long tasks beyond 50 ms each.
"Frames > 34 ms" counts frames that dropped at least one frame at 60 Hz. All times are at 5× slowed CPU, so a real
phone is roughly 2–5× faster, depending on the model.

## Before → after

| Step | to next frame (ms) | long tasks | longest task (ms) | blocking time (ms) | frames > 34 ms | worst frame (ms) | layout shift |
|---|---|---|---|---|---|---|---|
| First start (empty phone) | 604 → 663 (first story) | 11 → 5 | 370 → 364 | 916 → 722 | 12 → 8 | 558 → 531 | 0.13 → 0.33 * |
| Start, next time | 143 → 160 (first story) | 9 → 3 | 95 → 100 | 193 → 114 | 10 → 4 | 167 → 180 | 0 → 0 |
| Tab Forside → Live | 136 → 26 | 2 → 1 | 105 → 88 | 58 → 38 | 2 → 1 | 130 → 86 | 0 → 0 |
| Tab Live → Analyser | 26 → 37 | 2 → 0 | 74 → 0 | 30 → 0 | 1 → 0 | 129 → 31 | 0 → 0 |
| Tab Analyser → Forside | 101 → 21 | 3 → 0 | 72 → 0 | 32 → 0 | 3 → 0 | 123 → 18 | 0 → 0 |
| Open a story (Live) | 75 → 55 | 0 → 0 | 0 → 0 | 0 → 0 | 4 → 1 | 70 → 51 | 0.08 → 0 |
| Open Udvikling | 238 → 128 | 1 → 1 | 201 → 108 | 151 → 58 | 1 → 1 | 231 → 121 | 0 → 0 |
| Back from Udvikling | 163 → 4 | 3 → 0 | 125 → 0 | 98 → 0 | 3 → 1 | 162 → 41 | 0 → 0 |
| Open Begreber A–Å | 193 → 110 | 1 → 1 | 161 → 94 | 111 → 44 | 1 → 1 | 188 → 104 | 0 → 0 |
| Open a wiki page (Iran) | 37 → 36 | 1 → 1 | 94 → 102 | 44 → 52 | 1 → 2 | 113 → 125 | 0.10 → 0.10 |
| Open an answer from it | 54 → 51 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 2 | 47 → 51 | 0.10 → 0.10 |
| **Background reload**, 2 new stories, reader 1,800 px down in Live | 210 → 88 | 1 → 0 | 136 → 0 | 86 → 0 | 2 → 1 | 170 → 54 | 0 → 0; **the row being read jumped 140 px → 0 px** |
| **Background reload while the finger scrolls Live** | – | 1 → 0 | 159 → 0 | 109 → 0 | 1 → 1 | 191 → 53 | 0 → 0 |
| Scroll Live (4,000 px flick) | – | 1 → 0 | 51 → 0 | 1 → 0 | 1 → 0 | 85 → 15 | 0 → 0 |
| **Pull to refresh** (Forside), 2 new stories | – | 3 → 0 | 92 → 0 | 87 → 0 | 4 → 1 | 170 → 37 | 0 → 0 |
| **Intro** (the short writing, after a long break) | – | 10 → 3 | 536 → 238 | 657 → 244 | 12 → 4 | 652 → 304 | 0 → 0 |
| Intro, second time on the same phone | – | 8 → 3 | 524 → 126 | 604 → 135 | 11 → 3 | 647 → 201 | 0 → 0 |

The DOM after start is the same: 2,201 → 2,187 elements. The phone keeps 295 → 736 thousand characters of news and
files in its own storage (out of about five million allowed). The extra is moves.json and the wiki's two small index
files, kept so the first screen is complete.

\* **First start (empty phone).** My script marks the intro as already seen, so it measures a start with nothing on the
phone and nothing in front of it. A real first visit always shows the long intro ("Kom i gang") over the page for
several seconds, so the moving rows never show. The two new answer-line and wiki files arrive after the first drawing
and are kept from then on. On every later start (the "Start, next time" row) nothing moves at all. Before, the answer
line under the main story pushed the page down by 87 px, and the developments pushed it down by 270 px. The old
measurement did not count these jumps, because the old app rebuilt the page instead of moving rows.

What the owner described, against the numbers:

- **"Refreshing lags oddly" (pull-to-refresh and background reload).** No long task is left. The row being read no
  longer moves (140 px before). A reload that comes while the finger is on the screen waits until the scroll is over.
- **"Animations can stutter".** During a scroll or a pull, at most one frame is late, the worst at 37–54 ms. Before,
  up to four frames were late, the worst at 170 ms. The intro drops 4 frames instead of 12.
- **"Pages open slowly".** A tab switch takes 21–37 ms to its next frame, from up to 136 ms. Back from a side page
  takes 4 ms, from 163 ms. Udvikling and the A–Å index open in about half the time.

## What was slow, and what I changed

1. **Date formatting.** `toLocaleTimeString` and `toLocaleDateString` with options build a new formatter at every
   call. Drawing Live called them some 300 times, which cost about 100 ms at start on its own. Now there is one
   formatter per format, made once (`FMT`), with the same Danish output.
2. **Reloads.** Before, every reload rebuilt the page with `innerHTML`. Now the page is patched (`morph`):
   - the new page is built as a fragment and set against what is already there;
   - an unchanged row keeps its elements and its picture;
   - a changed row gets only its changed text and attributes;
   - a new row is put in, and only a genuinely new story rises in and glows for a moment (opacity and transform only).

   The first row under the top bar keeps its place on screen (`placeOf` / `restorePlace`). A reload's drawing waits
   while a finger is down, the pages are moving, or the page scrolled in the last 300 ms (`renderSoon`).
3. **Files that have not changed.** The news, digest, summaries and front files, and the wiki and answer files, are
   compared as text. An unchanged file is neither parsed nor drawn again. Most reloads change nothing, because the
   radar writes every five minutes and the app looks every two. The `JSON.stringify` comparisons of summaries, titles
   and the front page are gone.
4. **Copies on the phone.** The phone keeps the very text it received, written in an idle moment
   (`requestIdleCallback`). Before, it re-serialised the whole news object and wrote it at once in the middle of the
   reload. The old separate copies `lastSums` and `lastTitles` are removed once.
5. **Nothing moves at start.** The developments (moves.json) and the two small wiki files (the A–Å index and the
   answers' index) are kept on the phone too. The first screen therefore already has its answer line, its links and
   its timeline. Each of these files is fetched again behind the screen and drawn again only if it changed.
6. **Tab switches.** There is no forced layout any more:
   - the title's motion is a Web Animation, not a class plus `offsetWidth`;
   - the pill's positions under the tabs are measured once (again when the tab bar changes size), not at every tap and
     every scroll event;
   - a tab page that is already up to date is only shown, not drawn again.
7. **Side pages.** Udvikling, an answer, a wiki page and A–Å hid the tab pages with `visibility: hidden`. That made the
   phone restyle every row of every page each time a side page opened, about 100 ms. Now they use
   `content-visibility: hidden`, which keeps their place and scroll and costs nothing; `visibility` stays as a
   fallback. "Back" went from 163 ms to 4 ms.
8. **The neighbour pages** are drawn in idle callbacks, never while a finger is down, the pages move or the intro writes.
   A stale page that a swipe brought into view is drawn first.
9. **Opening a story.** It is laid out at once, and its contents fade and settle in. Before, a `grid-template-rows`
   animation laid out the whole list again in every frame. The fold of the other stories no longer needs the
   "snap" work-around.
10. **Long lists.** Closed news rows (fixed height) use `content-visibility: auto` with their exact height, so rows out
    of sight are neither laid out nor painted, and the page measures the same. I tried the same on the 321 answer rows
    and the 203 A–Å rows, but watching that many rows cost more on every frame than it saved, so they are left out.
11. **The intro.**
    - The pen's 650 polygons are worked out once and kept on the phone (`ink1`). Asking the path for a point is slow, so
      it is asked for every fourth point only, and the points between are laid on the straight line, at most a third
      of a pixel from the curve.
    - The polygons laid down within the same sixtieth of a second are joined into one shape: about 70 animated shapes
      instead of 650, with the same writing frame by frame. The screenshots of the before and after intros look the same.
12. **Service worker.**
    - The page itself, config.js and the wiki's files are served from the phone's copy at once, and the newest is
      fetched behind it.
    - They are kept under their plain path, so `?item=…` and the app's own check for a new version share one copy.
      A new version arrives at the next start, or when the app comes back (`checkVersion`, as before).
    - Versioned files stay cache-first. Data files are not handled by the service worker; they live on another host.
13. **Repeated computing.** The developments across days are worked out once per edition and archive, not again in every
    front-page block that names one. Thumbnails carry `width="64" height="64"` next to `decoding="async"` and
    `loading="lazy"`.

## What was removed (plain list)

- The frosted blur behind the tab bar. It is now solid like the top bar, which keeps the look. Also removed: the soft
  18 px shadow above it (the hairline stays) and the old "no blur" overrides for the top bar and the day bands.
- The blend mode on the big pictures' film grain. The grain is black specks, so plain transparency gives the same picture.
- The colour fade of a thumbnail when a story opens. It now turns to colour at once, with grayscale applied once and no
  animated filter.
- The height animation when a story opens or closes. It now opens at once and its contents fade in.
- The staggered rise of all rows at start. Only new rows rise now.
- The background-colour flash of new rows, replaced by a soft glow that fades by opacity.
- Colour and background transitions on rows, tab labels, the top bar's hairline, and the settings' switches, segments
  and colour circles. Their state changes at once; the movements (the switch's knob, a pill, a sheet) stay.
- Styles nothing used any more:
  - the old overview card (`.ov`, `.ov-row`, `.ov-h`) and the section glance (`.glance`, `.gl`);
  - `.follow-h`, `.follow h3`, `.thr-intro`, `.thr-h`, `.now-wait`, `.vh`, `.explain.top`;
  - `.title.swap`, `.view`, `.story.enter`, `.story.snap`;
  - the keyframes `spin`, `viewIn`, `titleIn` and `freshBg`.
- Code nothing used any more:
  - `inSection` (the section tabs are gone) and the never-set `anYear` / `azLetter`;
  - a click handler for `data-src`, which nothing produces;
  - the per-row `--i` style;
  - the forced layout before a story opens.
- Fixed for the text-size rule (`calc(Npx * var(--ts, 1))`): the four font sizes that were plain px (the search field,
  the admin code field, the text-size segment, "Flere farver").

Kept, as the owner chose, and made cheaper: the intro with the Ruqaa mark, the outlets' initials tiles, the long-press
admin, Læs/Del/Kopiér, the quiet motions (the title coming up, the page fading in, the pill gliding, the logo's rings on
pull-to-refresh, the glow of a new story). Reduce Motion is respected: the CSS rule as before, and every motion the app
starts itself (Web Animations, the new-row glow) checks `reduceMotion` first.

## Not changed, and why

- **Splitting movement.json / begreber.json.** Parsing is not the bottleneck: 10 ms each at 5× slowed CPU. The 100 ms
  when a wiki page or Udvikling opens for the first time is laying out a lot of new text for the first time (the second
  time takes 19 ms). Splitting the files would not change that, so the wiki build is untouched.
- **`text-wrap: pretty`** stays. It cost nothing measurable here (the first-time layout was the cost).
- **The first visit** is dominated by downloading the files and drawing everything for the first time, and the long
  intro covers it.

## Checks

- `node --check` on app.js and sw.js.
- `py -m pytest -q tests`: 192 passed, 5 skipped. This includes the new `tests/test_app_speed.py`, which keeps these
  out: blur behind bars; blend layers; animated filter, height or colour; px font sizes; toLocale formatting in the
  lists; stringify comparisons or synchronous copies in a reload; the enter animation; and a page served from the
  network before the phone's copy.
- No console errors. Phone screenshots at 430 px, 2x, light and dark: Forside (top and further down), Live, an opened
  story, two new stories after a reload (with the glow), Live Vigtigste, Udvikling, Analyser, a wiki page, and the intro
  mid-writing and finished, next to the same shots of the old version. They are in the session scratchpad
  (`speed/shots-after`, `speed/shots-before`).

## Open, for the owner's iPhone

- The real check is his own phone: pull-to-refresh, a reload while reading Live, a tab switch, opening Udvikling, and
  the intro after a night away.
- A new app version now shows from the next start or the next return to the app, not on the same start. That is the
  price of opening at once from the phone's copy.

## Professional build (2026-10-17, docs/hjerne/pro-plan.md)

Measured the same way (headless Edge, 390 × 844 at 3x, CPU 5× slowed, round 2's data set `?dev=r2`, three runs each,
medians). "Before" is `public/` at commit 63ea8d4 (the plan), "after" the professional build (`?v=20261017pro`).

| Step | to next frame (ms) | long tasks | longest task (ms) | blocking time (ms) | frames > 34 ms | worst frame (ms) | layout shift |
|---|---|---|---|---|---|---|---|
| First start (empty phone) | 654 → 652 (first story) | 4 → 6 | 384 → 320 | 816 → 722 | 8 → 10 | 567 → 505 | 0.19 → 0.42 * |
| Start, next time | 173 → 179 (first story) | 3 → 3 | 114 → 124 | 132 → 174 | 4 → 4 | 204 → 206 | 0 → 0 |
| Tab Forside → Live | 28 → 25 | 1 → 1 | 90 → 51 | 40 → 1 | 1 → 1 | 88 → 46 | 0 → 0 |
| Tab Live → Analyser | 37 → 33 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 33 → 29 | 0 → 0 |
| Tab Analyser → Forside | 22 → 20 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 21 → 25 | 0 → 0 |
| Open a story (Live) | 56 → 57 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 1 | 54 → 54 | 0 → 0 |
| Open Udvikling | 133 → 133 | 1 → 1 | 114 → 111 | 64 → 61 | 1 → 1 | 125 → 129 | 0 → 0 |
| Back from Udvikling | 3 → 2 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 1 | 50 → 54 | 0 → 0 |
| Open Begreber A–Å | 116 → 122 | 1 → 1 | 100 → 106 | 50 → 56 | 1 → 1 | 104 → 117 | 0 → 0 |
| Open a wiki page (Iran) | 39 → 104 ** | 1 → 1 | 104 → 81 | 54 → 31 | 2 → 2 | 129 → 100 | 0.10 → 0 |
| Open an answer from it | 56 → 83 ** | 1 → 1 | 50 → 68 | 0 → 18 | 2 → 1 | 54 → 79 | 0.10 → 0 |
| Background reload, 2 new stories, reader 1,800 px down in Live | 122 → 133 | 0 → 1 | 0 → 51 | 0 → 1 | 2 → 2 | 91 → 101 | 0 → 0; the row being read 0 → 0 px |
| Background reload while the finger scrolls Live | – | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 1 | 54 → 59 | 0 → 0.02 |
| Scroll Live (4,000 px flick) | – | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 13 → 8 | 0 → 0 |
| Pull to refresh (Forside), 2 new stories | – | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 1 | 38 → 50 | 0 → 0 |
| Intro (the short writing) | – | 3 → 3 | 261 → 274 | 270 → 317 | 4 → 4 | 334 → 345 | 0 → 0 |

DOM after start: 1,998 → 2,064 elements; kept on the phone: 736 → 736 thousand characters (Gem adds only what the
reader saves).

The plan's checks hold: no layout shift on later starts, tab switches 20–33 ms to the next frame (≤ 40), no new long
task at start (3 → 3), the row being read never moves on a reload, scrolling and pulling drop at most one frame.
What changed and why:

- **Rows that grow** (headlines are never cut) cost a little more layout at a start: blocking time 132 → 174 ms at 5×
  slowed CPU (roughly 10–20 ms on a phone). The row size estimate for rows out of sight was raised to a typical row
  (104 and 90 px) so rows coming into view barely move what follows.
- ** **A wiki page and an answer open complete.** After the first visit to Analyser the library (movement.json,
  begreber.json) is fetched in a quiet moment for Gem's offline reading. A page therefore draws whole in its first
  frame instead of drawing its head and then pushing it down when the file came (layout shift 0.10 → 0; blocking time
  on the wiki page 54 → 31 ms). The first frame comes later because there is more to lay out.
- A background reload now has one task of 51 ms (1 ms over the 50 ms line) where there was none: the rows carry their
  screen-reader label and their meta items. The reader's row stays put and the frames stay smooth.
- \* **First start on an empty phone** (the measurement marks the intro as seen): the answer line now sits directly
  under the main story, so when the answers' index arrives after the first drawing it pushes more of the first screen
  down. A real first visit always shows the long intro over the page, and every later start shows nothing moving (0).

Checks: `node --check` on app.js and sw.js; `py -m pytest -q tests`; no console errors in the phone shots (430 px, 2x,
light and dark, text sizes 1 and 1.3) of Forside, Live (both orders, an opened story), Udvikling (folded, unfolded, the
long course), Analyser (search, area filter), an answer, a wiki page, A–Å, search (empty and with hits), Gemt,
settings, the intro, a deep link, offline, a story that left Live and the fixed front page; the back paths (logo,
history), `?forlob=`, `?svar=`, `?item=` and the admin long press checked by script. Shots: session scratchpad
`pro/b3/s1` … `s5` (before: `pro/b3/shots0`); scripts: `speed/measure.js`, `speed/compare-pro2.js`.
