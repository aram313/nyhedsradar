# Khabar, made professional – the lead designer's plan (2026-10-17)

The owner's request (17/10): *"Gennemgå alle sidens funktioner og brugervenlighed, og gennemtænk en bedre måde at vise
det og øge brugsfunktionerne, så det bliver professionelt."*

This plan builds on three audits of today's app (news, knowledge pages, craft: 81 findings and 18 proposed functions)
and my own pass over the local preview with the editor's real run of 17/10 (`?dev=r3`) and live khabar.nu. The
screenshots are 430 px at 2x, light and dark, text size 1.3, in the session scratchpad (`pro/lead`, `pro/kn`,
`pro/shots`). Nothing in the app is changed by this document.

**The look stays khabar.nu.** It keeps the Ruqaa mark, the Dæmpet/Notion palettes, the compact rows with small
black-and-white pictures and initials tiles, bold keywords, the ochre for the movement, the bottom tabs, the quiet
motion and the speed of round 2. The plan refines; it replaces nothing.

---

## 1. What "professional" means here

The best news apps (BBC, Reuters, AP, the Guardian, DR, Apple News, Al Jazeera, Le Monde) share five traits. Khabar
already has the base (speed, calm, a clear hierarchy on the front page), but it falls short on each of them:

| Trait | The best apps | Khabar today (measured on r3 at 1.3) |
|---|---|---|
| **One voice per typeface** | News in the sans, opinion and the publisher's own voice set apart | The serif carries three voices: the editor's lede, development names and quotes, and the movement. On Windows and Android, `--serif` falls back to the same Georgia |
| **Signals keep their meaning** | 'Breaking' or 'Top story' a handful of times a day | Red 'Topnyhed' sits on 48 % of the day's stories, with a red dot on every block title, a red date and red dots in search |
| **What informs is never cut** | Headlines and sources wrap and the row grows | At 1.3, 22 of 40 Live headlines end in '…'; the outlet name drops out ('New York …') |
| **Every state is designed** | Loading, empty, offline, error and 404 each have a message and a way on | With no saved copy and no network, the skeleton shimmers for good and the bar says 'henter …' |
| **Everything can be shared and found** | One search, and share on every article and topic page | An answer, a wiki page or a development cannot be shared. Two separate searches. The shared text uses a teaser, not the summary on screen |

Each part below fixes one of these. Section 7 orders the work.

**Binding rules (CLAUDE.md, unchanged by this plan).** Compact and text-first. Minimal colour: red only for big stories
and live, ochre only for the movement. Bold keywords guide the eye. Thumb-first, 44 pt. Quiet, functional motion.
No explanatory paragraphs in cards. Overskuelighed før fuldstændighed. Block titles and day markers never alike. The app
never mentions Claude. No feedback buttons. The owner's admin only by long press. Nothing follows a person: no ids, no
consent prompts, and the reader's own choices stay on the phone. No analysis by Claude or Khabar. Every font size is
`calc(Npx * var(--ts, 1))`. Bump `?v=` on every change. Speed must not regress (notes-r2-speed.md).

---

## 2. The visual system

### 2.1 Type scale: eight steps instead of 28 sizes

style.css uses 28 different font sizes, from 9.5 to 28 px, often in half-pixel steps. That is why the rhythm feels
uneven. The fix is one ramp of named tokens, each `calc(Npx * var(--ts, 1))`, defined once on `:root`. Every rule then
uses a token, not a number.

| Token | Size / line | Weight | Used for |
|---|---|---|---|
| `--fs-cap` | 12 / 1.2, caps +.07em | 750 | Labels inside a block (SÅDAN UDVIKLEDE…, DÆKNING), the day pill, settings headings |
| `--fs-meta` | 13 / 1.35, tabular | 400 (outlet 600) | Meta lines, time columns, counts, credit lines |
| `--fs-small` | 14.5 / 1.42 | 400 | Secondary text: a development's last line, coverage rows, hints |
| `--fs-body` | 16 / 1.36 | 480 (keywords 700) | Row headlines, chips, buttons, settings rows |
| `--fs-read` | 16.5 / 1.5 | 400 | Reading text: an opened story's summary, the answer's text, readings |
| `--fs-lead` | 19 / 1.27 | 560 | The lead story, the hero headline (20 today), development names, the lede |
| `--fs-block` | 22 / 1.18 | 780 | Block titles (Dagens historie, Danmark, Live) |
| `--fs-title` | 26 / 1.16 | 760 | Page titles: Udvikling, an answer, a wiki page, Indstillinger |

Exempt: the intro mark, the logo, the monogram tiles and the admin statistics. The admin block is private, so its
9.5–10 px chart axes may stay.

**Text size reaches everything, capped in the chrome.** Today `--ts` is set on `#list`, so the top bar, the tab labels
(fixed at 10.5 px) and the settings sheet never grow. The change: `applyTextSize` sets `--ts` on `<html>`, and the bar,
tabs and sheet use `--ts-c: min(var(--ts), 1.2)`, the way iOS caps its bars. The tab label becomes
`calc(11px * var(--ts-c))`. The settings hint 'Gælder nyhederne' then goes.

### 2.2 Two voices, two typefaces

- **The app's sans is Khabar's voice and the outlets' voice.** That covers the lede, block titles, development names,
  quotes from outlets, the intro text and every row.
- **The serif is the movement's voice only.** That covers `.ht` and `.ht-*`, the Analyser rows (the movement's
  titles), the answer reader, the wiki's readings and the ochre answer line.
- What changes:
  - `.lede p` becomes sans, `--fs-lead`, weight 500, at most three lines.
  - `.thr h3` and `.fol-row b` become sans at weight 700.
  - `.quote q` becomes the sans in italic at `--fs-body` with »«. An outlet's quote is not the movement's.
  - `.intro-lead` becomes sans.
  - The initials tiles keep Georgia: they are logos, and the owner likes them.
- **Test.** No `Georgia` and no `var(--serif)` outside `.ht*`, `.an-*`, `.rd-*`, `.wk-*`, `.th b`, the intro mark
  and the logo.

### 2.3 Spacing, radii, lines

- **Spacing scale:** 4 · 8 · 12 · 16 · 24 · 32 (`--s1` to `--s6`).
- **One left edge per level.** Page text starts at 16. A panel sits 12 from the screen edge with 12 inside, so panel
  text starts at 24. Today panel text starts at 20, 22, 24 or 26, depending on the block.
- **Rhythm.** 28 px between blocks, 8 from a label to its content, and 12 above and below a row's text.
- **Radii.** 12 for buttons, the answer line and quotes. 16 for panels: Dagens historie, Følg udviklingen, `.thr` and
  `.ht-box`, which today use 14, 16, 18 and 20. 20 for sheets. Chips stay round.
- **Separators.** 1 px `--line` between rows everywhere. Today some are .5 px and some 1 px.
- **Elevation.** Only the sheet, the toast and the fresh pill carry `--shadow`.

### 2.4 Colour: the same palettes, used with discipline

- **Red only means live or big.**
  - The red dot leaves `blockHead()`. It stays only on the front page's Live block and the Live tab's own small dot.
  - The lede date becomes `--text-3` caps.
  - The search page's development rows take their section dot.
  - The Live tab label stays like the other tabs; its dot alone says something is new.
- **'Topnyhed' is rationed.** At most the five strongest big stories of the Danish day carry the label: the editor's
  picks first, then rank, and only for 12 hours after publication. It never appears inside the editor's front-page
  blocks or in Vigtigste, where the order already says it. The radar's `big` flag is unchanged for push and rank. The
  ration is one filter in `meta()`.
- **New stories.** The 'new' dot moves from the screen's left edge (x = 5) to sit before the time, inside the row.
- **The day pill is lighter.** It becomes `--fill-2` with `--text`, 12 px caps and the hairline kept. Today it is the
  brightest thing on the dark screen (white on #191919). It still looks nothing like a block title.
- **Dark segmented controls.** The selected segment goes one step lighter than the track (`--fill-2` on `--fill`, plus
  700 weight). Today it is darker, so it reads as pressed in.
- **Contrast.** Every text token is at least 4.5:1 on its surface in all 8 palettes, and the ochre pairs are already
  checked. Add `scratchpad/pro/contrast.js` as a test so a palette change cannot slip below.

### 2.5 One icon set

- **The set.** The inline sprite in index.html stays the only icon set: a 24-grid with 1.8–2.0 strokes and round caps
  and joins. Glyphs in CSS go: `›` and `↗` after timeline steps become `i-chev` and `i-open` at 12 px, the bar's back
  mark (two CSS borders today) becomes `i-back`, and the ✕ becomes `i-x`.
- **Added to the sprite, the same stroke family:** `i-back`, `i-save` and `i-saved` (bookmark outline and filled),
  `i-refresh`, `i-offline` and `i-plus`. Nothing else.
- **Sizes.** 23 in the bar, 25 in the tabs, 19 in action buttons, 16 in mini buttons and chips, 15 for trailing
  chevrons. No emoji anywhere.

### 2.6 Components: one of each

| Component | Rule |
|---|---|
| **Row** | Four forms, as today: `pic`, `tick`, `lead` and `hero`. Closed headlines never lose their informing words. The clamp goes to 4 lines, and the row grows with `contain-intrinsic-size: auto calc(…)`, so its real height is remembered after the first layout (section 2.8 has the speed check). The text column is top-aligned: the Live time column sits on the headline's first line, not centred against the row. |
| **Meta line** | Up to four items in this order: `Topnyhed` or `Kommentar`, section dot and word (only on mixed lists), **outlet**, time. The outlet is never cut (`flex: none`). When room runs out, the section word goes first, keeping its dot, then the time. The line breaks between items, never inside one, and never starts with '·' (each item gets its separator as `::before` and `nowrap`). |
| **Block head** | `blockHead(title, more)`. Title at `--fs-block`, no dot, with the 'more' link right-aligned in the same row (44 px hit area): 'Alle ›', 'Se alt i Live ›'. It replaces the three 'more' styles in use today (`.more`, `.now-more`, the big grey `.wide.soft`). |
| **Label** | Caps at `--fs-cap` in `--text-3`, only inside a block or panel. It is never a block's title. |
| **Day pill** (`.day`) | Time only: the days in Live and the years in Analyser. It sticks under the bar. |
| **Group header** (`.grp`, new) | Every other group: search result groups, A–Å letters and settings groups. The `.arch-h` look, with caps in `--text-3` and a hairline, sticky where it helps. So search groups no longer look like days. |
| **Action row** | `Læs · Del · Kopiér`, plus a square bookmark (44 × 44, icon only, `aria-label` 'Gem' or 'Gemt') on stories. On knowledge pages it is `Del · Kopiér · Gem`. Same buttons and sizes everywhere. |
| **Mini button** | 40 px visible with an inset `::after` hit area to 44. It names its target: 'Udvikling: Iran og angrebet ›', 'Andre medier 2'. |
| **Chip** | 36 px visible, 44 hit area. A wiki chip on the ochre tint, a search chip on `--fill`. |
| **Segmented control** | 44 px high, with the dark fix above. |
| **Quiet text button** | The one 'Vis flere (14)' style on every page: `--fs-body` 600, `--text-2`, 44 px, left-aligned with the content. |
| **State block** | One `stateBlock(kind, what, actions)` for empty, offline, error and 404 (section 2.7). |

### 2.7 States, all designed

| State | When | What the reader sees |
|---|---|---|
| **Loading** | The first fetch with nothing on the phone | Skeleton rows for at most 4 s; then the offline or error block |
| **Offline, with a copy** | A fetch failed, the phone's copy shows | The bar reads `offline · 10.53` in `--text-3`, and the page notice stays as today. It returns to normal by itself |
| **Offline, nothing kept** | The first start without network or with the data host down | `Ingen forbindelse. Nyhederne kommer, så snart telefonen er på nettet.` + [Prøv igen]; the bar reads `ingen forbindelse` |
| **Recovery** | Always | `addEventListener('online', () => load(true))`, and a load on `visibilitychange` when the last attempt failed |
| **One file failed** (answers, wiki, moves) | As now | `Kunne ikke hente svaret lige nu.` + [Prøv igen], the same `retry()` everywhere, including the answer reader (today it shows the bare question) and the wiki page (today it has no button) |
| **Empty** | No hits, nothing saved, no development today | One line, plus a way on (search: 'Se svarene om »x« ›') |
| **Not found** | An unknown `?begreb=`, an old `?svar=`, or an `?item=` that has left Live | `Siden findes ikke.` / `Historien er ikke længere i Live.` + [Søg efter den] and [Alle begreber A–Å] |
| **New content** | A reload brings stories | The fresh pill as today, plus 'N nye historier' read aloud through the existing `#toast` (role=status) |
| **Stale** | The data is old | Unchanged: only the box on the page, the bar stays quiet |

### 2.8 Speed stays

- **The rules.** Every change keeps round 2's rules (CLAUDE.md, the speed section). Only transform and opacity move,
  nothing is drawn while a finger is down, and nothing is parsed twice.
- **Rows that grow.** The one structural change is that rows grow (2.6), and it is safe for two reasons:
  - `overflow-anchor: none` and the `placeOf`/`restorePlace` patch already keep the row being read in place;
  - rows that grow below the screen never move what is on it.
- **The check.** After that step:
  - rerun `tests/test_app_speed.py` and the round-2 measurements (the scripts in the scratchpad's `speed/`);
  - require 0 layout shift on later starts;
  - require tab switches ≤ 40 ms to the next frame;
  - require no new long task at start, at 5× CPU.
- **New functions.** They are drawn only when opened: Gem, search scopes, the catch-up line. Anything they store is
  written in `idle()`.

### 2.9 Time and words: one formatter, one vocabulary

- **`ago()` becomes `stamp()`.**
  - 'nu' under a minute, then 'N min' up to 9 minutes (`Math.floor`, so '60 min' never shows).
  - After that 'kl. 10.16' today, 'i går kl. 21.34' yesterday, 'lør. kl. 23.32' within the week, and '12/10' after it.
  - Time columns (Live, timelines, the Live block) show only '10.16'. A quiet day row ('I går', 'Torsdag') stands
    before the first line of another day.
- **Timelines run newest first everywhere**, like a wire and like the owner's chosen Al Jazeera style. That covers the
  front page package, the Udvikling cards and the wiki's 'I nyhederne nu'. Today the front page alone runs oldest first,
  crosses midnight without saying so, and '23.08' reads like a date.
- **Vocabulary.**
  - A development (the topic) is an **udvikling**, and each of its lines an **opdatering**. 'Linjer' and
    '62 udviklinger' go.
  - A card or row reads 'fulgt i 8 dage · senest kl. 10.36', and a count, where one helps, '3 nye i dag'.
  - The bar's time is the only 'opdateret'. Udvikling says 'Resumé kl. 10.57'.

---

## 3. Each view, refined

### 3.1 Top bar and tabs

- **Bar.**
  - The mark and the page name stay. The status becomes '10.53' with a small `i-refresh`, the visible form of what is
    a hidden refresh button today. Offline it reads 'offline · 10.53'.
  - On side pages the back mark is `i-back`.
  - The bar's magnifier opens the one search (5.2) with the scope that fits the page: Svar on Analyser, an answer, a
    wiki page and A–Å.
- **Tabs.**
  - While an answer, a wiki page or A–Å is in view, the **Analyser tab stays selected**. Today none is, and the red Live
    label looks like the current tab.
  - A tap on the selected tab scrolls its page to the top, and on a side page it goes back to the list at its kept
    place (iOS's pop to root).
  - The Live label is no longer red.

### 3.2 Forside (the editor's composition, and the fixed page in the same pieces)

The first screen, from the top:

```
LØRDAG 17. OKTOBER                                         [del]   ← date in text-3 caps; share = 'Del dagens overblik'
Trump sætter sanktioner på pause, houthierne rammer Aden og       ← lede: sans 19/500, ≤ 3 lines, tap → Udvikling
Saudi-Arabien, og Unicef melder om 340 dræbte børn i Gaza.
Siden i går kl. 22.14: 9 nye · 1 nyt svar                          ← 'Mens du var væk' (5.3), only after ≥ 3 h away
┌ Dagens historie ───────────────────────────────────┐            ← block head, no red dot
│ [hero picture + headline + meta]                    │
│ Hizb ut-Tahrirs svar · 28/6/2026 ›  (ochre line)    │            ← moved up: directly under the main story
│ UDVIKLING: IRAN OG ANGREBET ›                       │            ← the label names (and opens) the development
│ 10.36  Irans Ekspertforsamling: …                   │            ← newest first, three updates
│ 04.42  Revolutionsgardens flåde: …                  │
│ I går                                               │            ← day row where the day changes
│ 23.08  Donald Trump: …                              │
│ [with-story row]                                    │
└─────────────────────────────────────────────────────┘
```

- **The lede.**
  - It is smaller and in the sans. At 1.3 it takes three lines, not seven, so the lead story plus two or three
    headlines fit above the fold.
  - `editor.py publish` (voice) refuses a lede whose first clause shares 60 % or more of its stems with the first
    top block's title. The lede then names the day's other stories, as a standfirst does.
- **The package.**
  - The answer line moves directly under the main story. Today it sits after the 'with' story and looks as if it
    belongs to Mette Frederiksen and Zelenskyj.
  - The timeline label names its development and opens it.
  - If the editor's timeline topic shares fewer than three stems with the main story, the app uses `threadFor(story)`
    instead, so the package and its 'Udvikling' button show the same development (`editor.py check` flags it).
- **List blocks** ('Danmark', 'Gaza og Vestbredden'). When every row shares one section, the rows go without the
  section word (`tag: false`). Each row then reads 'BT · i går kl. 21.34', and the outlet always fits.
- **Følg udviklingen.** The block title stays. The names are in the sans at 700, and the meta reads 'fulgt i 8 dage ·
  senest kl. 09.47'.
- **Live block.**
  - The block head is 'Live', with the one red dot of the front page and 'Se alt ›' in its header row (44 px; today
    it is 19 px tall).
  - The rows use `display()` headlines (the editor's, never the outlet's curiosity headline) and skip commentary.
- **The foot.** One quiet row, 'Olie og brændstof – priser nu ›', which links `energi/` without touching its code.
  Under it, the read-and-chosen line as today.
- **The fixed page** gains a 'Danmark' block: the 3 strongest confirmed Danish stories not shown above, with
  `tag: false`, after Døgnets vigtigste. It uses the same block heads and rows as the composed page.

### 3.3 Live

- **The control.** The segmented control is 44 px high.
- **Day pills.** They are the lighter pill (2.4), and stay the only pill in the app.
- **Ticker rows.**
  - The time column sits on the first line, and the headline gets up to 4 lines.
  - The meta line reads `Topnyhed` (rationed) or `Kommentar`, then the dot and section, then the outlet.
  - The 'new' dot sits before the time.
- **Commentary is labelled.** The radar marks `kind: 'kommentar'` from the URL path (`/kommentar`, `/kommentatorer`,
  `/debat`, `/opinion`, `/analyse`, `/leder`, `/blogs`) and from `curious()`'s opinion tails, and carries it in
  app.json. The app shows 'Kommentar' first in the meta line (`--text-2`, 600, never red). The editor's input lists the
  kind, so commentary is never a 'top' block.
- **'Vis ældre'** is the quiet text button.

### 3.4 An opened story

```
[headline, full, its wiki names linked]
Topnyhed · Mellemøsten · Anadolu · kl. 09.20
[summary at --fs-read in --text]                         ← the editor's; a cleaned teaser, or nothing
Resumé ud fra overskrifter og indledninger · Original: »…«   ← ONE credit line, 13 px, ≤ 2 lines (tap: full)
[ Læs ][ Del ][ Kopiér ][🔖]
Hizb ut-Tahrirs svar · 27/9/2026 › (ochre)              ← unless the front page shows that answer already
Houthierne · Yemen · Saudi-Arabien                       ← up to 3 wiki chips (ochre), only in an opened story
[Udvikling: Riyadh-lufthavnen og Houthierne ›] [Andre medier 2 ⌄]
Olie og brændstof – priser nu ›                          ← only when the text names olie/benzin/diesel/Brent/OPEC/Hormuz
```

- **Teasers are cleaned** in the app and at the radar's intake.
  - Trailing calls to action go: 'Følg udviklingen … her', 'Læs mere', 'Se video', 'Live:' and URLs.
  - A teaser that shares fewer than two stems with the headline is dropped. The reader then sees nothing rather than a
    mismatch, and the 'Andre medier' headlines carry the story.
- **The two notes become one line.** The italic 'Resuméet bygger på …' and 'Originaloverskrift på engelsk: »…«' merge
  into the credit line above.
- **An answer shows once.** `detail()` gets the front page's `svarSet` and the package's own answer as `skip`, so the
  same answer never shows twice on one screen.
- **Headlines with an outlet prefix.** An editor headline beginning 'X:' where X is one of the story's other outlets
  shows that outlet in the meta line and on Læs, the same as `display()` does for a curiosity fallback. Any other 'X:'
  prefix is dropped. `voice.check_headline` allows the prefix only when the outlet is the claim's speaker.

### 3.5 Udvikling

- **Its own address.** The page gets `?forlob=<key>` in `sideUrl`, so the back gesture and a shared link both name it.
- **Each card.**
  - The name is in the sans, followed by 'fulgt i 8 dage · senest kl. 10.36' and its updates, newest first, with day
    rows.
  - At its foot, quiet [Del] [Kopiér] buttons. The text is WhatsApp-ready: the name, today's updates as '- 10.36
    Who: what' (at most 6), and 'via khabar.nu/?forlob=<key>'.
- **The whole course.** An unfolded course shows today and the last two days, then 'Vis hele forløbet (40 mere)'
  through the existing `data-step`. Today 'Iran og angrebet' unfolds to 12,277 px at once. While the reader is inside
  an unfolded card, a sticky line with its name and a fold chevron stays in view (transform only).
- **The header.** 'I dag · Resumé kl. 10.57' with [Del resumé]. The share button reaches 44 px.

### 3.6 Search: one search (5.2)

```
[ Søg i nyheder, svar og begreber        ✕ ]
 Alle · Nyheder · Svar · Begreber                      ← scope, preset by the page you came from
SENESTE SØGNINGER   houthierne · Khilafah · Sudan      ← on the phone only, ≤ 5
POPULÆRT NU         Vestbredden · Gaza · Rusland · …   ← Danish wiki page names, once each
UDVIKLINGER         • Iran og angrebet   fulgt i 8 dage ›
GEMT (4) ›                                              ← Gem (5.1)
```

- **Results come in groups with `.grp` headers, in this order:**
  - Begreber, as ochre chips;
  - Udviklinger;
  - Hizb ut-Tahrirs svar: the top 3 `anRow`s with `mark()` and 'Alle n svar ›';
  - På Khabar, the stories in Live;
  - Andre nyheder, where rows sharing their first 6 stems collapse into one and `title_da` shows where it exists.
- **No hits** reads 'Ingen nyheder de seneste to døgn om »x«', with a way into the answers or the A–Å index.
- **Data.** `search.json` is still fetched only when someone searches, and the answers' index is already on the phone.

### 3.7 Analyser

- **One compact title line.** 'Hizb ut-Tahrirs svar' with '321 svar · 2004–2026' small on the same line. Today a
  two-line H1 and a subtitle push the first answer 42 % down the screen.
- **A sticky strip under the bar** holds the search field and one sideways chip row:
  - first [Begreber A–Å], an ochre chip;
  - then the areas by number of answers ([Alle] [Palæstina] [Syrien] [Iran] [Ukraine og Rusland] [Yemen] … [+ n]),
    which filter the list in place, are remembered on the phone, and start it with 'Siden om Palæstina ›';
  - after a hairline, the years, which jump to their band.
  - Search and filters stay reachable at 2023.
- **Why a hit matched.** A query that names a wiki page or alias gets a first row 'Khilafah · Begreb · 18 svar ›'. A row
  that matched only through that page carries '· via Khilafah'. A hit in the question shows the marked phrase under the
  title (one line).
- **Rows.** An opened answer's row is drawn in `--text-2`, from its numbers kept on the phone (`ansSeen` grows to 400).
  Rows become `<a href="?svar=<nr>">`, so a long press can copy the link.

### 3.8 The answer reader

```
Hizb ut-Tahrirs svar af 8/12/2024 · Syrien · Originalen ↗   ← byline with the source link
Begivenhederne i Syrien og Assad-regimets fald               ← --fs-title, serif
[ Del ][ Kopiér ][ Gem ]
Nyeste svar om Syrien · 27/1/2026 › SDF's tilbagetog          ← ochre, only when a newer answer exists
SPØRGSMÅLET … · SVARET KORT … · readings · Begreber i svaret
Svaret henviser til … · Senere svar, der henviser hertil …    ← cites_nrs read in reverse; no new data
I NYHEDERNE NU (≤ 4, display() headlines, open in Live)       ← answerFor's test in reverse; none → no strip
[Åbn originalen]
```

- **The share text.** '*<title>*', then the first sentences of 'Svaret kort' (≤ 400 characters, ending at a sentence;
  they already carry 'Ifølge Hizb ut-Tahrirs svar af …'), then 'Originalen: <url>', then 'via khabar.nu/?svar=<nr>'.
- **Text fixes.**
  - Strip the build labels ('ÆNDRING:') in the movement build's inputs and rebuild.
  - Fix the 'Ifølge svaret og 27/1/2026' shortening. Shorten only when the date is followed by ':' or by a word other
    than 'og'; otherwise write 'Ifølge dette svar og svaret af …'.

### 3.9 A wiki page

- **Under the title.**
  - A contents row with real counts, 'Forløb 20 · Forhold 8 · Svar 80 · Nyheder 2'. Each item scrolls to its section
    below the bar, and only sections that exist are listed.
  - The paired page in one row: on a state page 'Iran – sagen · 31 svar ›', on the issue page 'Staten Iran · 80 svar ›'.
- **The action row** [Del] [Kopiér] [Gem]. The share text is '*<name>*', then the lead's first two sentences
  (attributed and dated), then 'via khabar.nu/?begreb=<id>'.
- **News under the lead.** When today's news names the page, 'I nyhederne nu' moves directly under the lead (at most 3
  rows), with `display()` headlines, bold keywords and section dots. Today it is last and uses the outlet's raw
  headline.
- **'Gennem årene'.**
  - It leaves out a row from the lead's own answer that overlaps the lead by 0.6 or more (the existing `like()`). The
    count 'Hele forløbet · n' still includes it.
  - Each row becomes a bold date label, 'Svar af 28/6/2026 ›', which is the 44 px link, followed by plain text that
    starts 'Ifølge svaret …'. Scanning by date gets fast, and the text stays text.
- **Section titles** are real headings (`role="heading"`, level 2 or 3).

### 3.10 A–Å

- The letter strip sticks under the bar, and its buttons are 44 px.
- A kind filter sits above A: Alle · Stater · Magter · Sager · Begreber · Aftaler.
- Under the filter come 8 chips of the most-used pages, by `n_answers`.
- An issue sits as an indented second line under its state ('– sagen · 31 svar'), not as its own near-identical row.

### 3.11 Indstillinger and the intro

- **Settings hold only settings.**
  - Notifikationer gets three switches (5.5).
  - The 'Energi' section and its paragraph leave settings. Energy and the two install guides move to a last quiet
    group, 'Mere'.
  - A hint line names the offline library ('Svarene og begreberne er gemt på telefonen · opdateret 15/10').
- **Deep links skip the intro.**
  - The inline script adds `intro-skip` whenever the address carries `item`, `svar`, `begreb`, `forlob`, `digest` or
    `tab`. Today a first-time reader who taps a shared link must press 'Kom i gang' first, and a notification after
    6 h waits 2.5 s for the pen.
  - A first visitor who came by a link gets `introSeen` when they leave the page.
- **The intro's three lines** match the app: Forside, Live, and Hizb ut-Tahrirs svar with Begreber. No 'how Khabar
  chooses'.
- **The iPhone install hint.**
  - On iPhone Safari outside the home screen, it shows once from the second visit: a one-line card at the top of
    Forside, 'Læg Khabar på hjemmeskærmen for at få notifikationer · Sådan ›' with `i-x`.
  - It is remembered on the phone. It is not a consent prompt.

### 3.12 Accessibility (no visual change)

- **Tab pages.**
  - The pages not in view get `aria-hidden="true"` in `setTab`/`settle`: an attribute toggle with no layout cost.
  - They also get `role="tabpanel"` with `aria-labelledby`, and the tabs get `aria-controls`.
- **Row labels.** A row's button is labelled 'headline. Outlet, kl. 10.17, Topnyhed', with `aria-hidden` on `.tx`, so
  VoiceOver reads the headline once.
- **Headings.** Day pills, year bands, letters and section titles are headings, so the rotor jumps by day or section.
- **Hidden rows.** `content-visibility: auto` may hide off-screen rows from VoiceOver. To check on the owner's iPhone:
  swipe through Live past the first screen. If rows are skipped, keep `content-visibility` only for rows 16 and on
  (`nth-child(n+16)`), then re-measure.
- **Tap targets.** Everything the audits measured below 44 pt is fixed through the components above: 'Se alt i Live'
  (24 px), the minis (34), the segments (40), the chips and jumps (36), the share buttons (36) and the logo (31).

---

## 4. Server-side changes the views need (radar and editor)

1. **The push headline follows the owner's headline rule.**
   - radar.yml gives the radar the digest branch's `summaries.json` titles as `.cache/summaries.json`, the same way
     `live.json` arrives.
   - `run.py` picks the editor's title for the id or a member, else `title_da`, else `title_tr`, else `title`. A
     candidate that `headlines.curious()` flags gives way to the teaser's first sentence.
   - The notification title stays 'Topnyhed · N medier'.
2. **`kind: 'kommentar'`** comes from URL paths and curious tails (3.3). It is carried in app.json, listed in the
   editor's input, and never used as a top block.
3. **Teasers are cleaned at intake** (3.4), in `feeds.tidy`.
4. **New `editor.py` checks:**
   - a lede that restates the top block (3.2);
   - an outlet prefix that is not the speaker (3.4);
   - a timeline topic that does not match the main story (3.2).
5. **The movement build:** strip 'ÆNDRING:'-type labels, plus a test that fails on an all-caps label of 4+ letters
   followed by ':' in any `text_da` (known acronyms excepted).
6. **Push kinds** for 5.5: `push.py` keeps `want` next to each subscription in `phones.bin` and filters in
   `everyone(phones, kind)`. `analyses.py` gets a 'new answer' push.

---

## 5. New functions: five chosen

I chose the functions that serve how these readers use Khabar. They gather material during the day, use it later in a
conversation, often with poor signal, and pass it on in WhatsApp. Every choice stays on the phone or rides the phone's
existing push subscription, so nothing follows a person.

### 5.1 Gem – save stories, answers and pages, readable offline

- **Why.** It is the one function every professional news app has. For a member preparing a conversation it is the most
  useful thing Khabar lacks. Today the workaround is sharing to oneself.
- **How.**
  - The bookmark square in a story's action row, and Gem in the action rows of answers and wiki pages.
  - `localStorage 'saved'` holds at most 200 entries, written in `idle()` inside try/catch:
    - a story's snapshot: id, the headline as shown, the outlet, the time, the link, the editor's summary and the
      `also[]` headlines;
    - for an answer or a page, only its nr or id.
  - The list opens as a side page, 'Gemt', reached from the search page's empty state and from a row in Analyser's
    strip. A saved story draws from its snapshot, so it opens offline and after it has left Live. Answers and pages
    draw from the viden files.
- **The offline library.** After the first visit to Analyser, `movement.json` and `begreber.json` are fetched in
  `requestIdleCallback`, but not on save-data or 2g. The service worker already keeps `/viden/*.json`. This is what
  makes saved answers truly offline.
- **Signals.** A save sends the same silent signal as a share, with no id. That is within 'silent share/copy/open
  signals'.

### 5.2 One search with scopes

- **Why.** Today news, answers and pages are three worlds. Typing 'houthierne' in the main search never shows the 12
  answers, and 'kalifat' in Analyser gives 18 answers with no word to show why. A reader preparing a talk wants 'Iran'
  across all of them.
- **How.**
  - Section 3.6: the scope control `Alle · Nyheder · Svar · Begreber` (preset by the page), grouped results, Danish
    suggestions from the wiki's names, and the last 5 searches on the phone.
  - Analyser keeps its own field as the list's filter (3.7).

### 5.3 Mens du var væk

- **Why.** Most openings come after a night or a working day. Today the reader hunts for small red dots.
- **How.**
  - After 3 h away (`backFromBreak`, the rule that already shortens the intro), one line under the lede: 'Siden i går
    kl. 22.14: 9 nye · 2 topnyheder · 3 opdateringer i Iran og angrebet · 1 nyt svar'.
  - Each part is a tap target: Live with the new rows marked, the development unfolded, or the answer.
  - It is computed from `lastSeen`, `isNew()`, `lineNew()` and `unseenAnswer()`. It fades after the first scroll or
    tab change (opacity only) and stores nothing new.
  - It holds no text of Khabar's own beyond counts.

### 5.4 Del dagens overblik

- **Why.** The group's own habit is posting 'Politiske nyheder – <dato>' lists. A ready daily brief saves members the
  composing and carries Khabar's links.
- **How.**
  - The small share icon on the front page's date line. That is the only share on the front page, so sharing stays
    secondary.
  - The text, built from `front.json`:
    - the heading '*Dagens nyheder – lørdag 17. oktober*';
    - the lede;
    - up to 5 lines '- *<editor's headline>* (Outlet) <link>';
    - 'via khabar.nu'.
  - It goes through `share()`/`copyText()`. Without a composition, the fixed page's top 5 are used. Only checked
    headlines are used, never analysis.

### 5.5 Notifikationer efter eget valg

- **Why.** Today it is all or nothing, about 15 a day. The kind these readers would value most, a new answer from
  Hizb ut-Tahrir, does not exist, and choosing types keeps people from turning everything off.
- **How.**
  - Three switches under 'Slå notifikationer til': Topnyheder · Dagens resumé kl. 21 · Nye svar fra Hizb ut-Tahrir.
  - The choice is kept on the phone and sent with the existing `{kind: 'sub', sub, want: […]}` (section 4, item 6).
  - The choice belongs to the subscription the phone already gave, so there is no new id and no prompt beyond the
    phone's own.

### Why the others wait

| Function | Why it waits |
|---|---|
| **Følg et emne/begreb** ('Dine emner' block) | It adds a personal block to a front page the editor composes, and it overlaps Gem and Mens du var væk. Better to see first how Gem and the catch-up are used. It also needs 'Følg' freed from today's button, which this plan renames. Next in line. |
| **Del som billedkort** | It would be a canvas renderer with the risk of a gimmick. An image of the movement's text also travels without its link, and so without its context and attribution. That is the owner's call, after Gem and sharing with links are in place. |
| **Filter i Live** (Danmark · Mellemøsten · Verden) | The owner removed the section tabs on 17/10 and chose one Live list. A filter brings the sections back by another door, so it needs his decision. It is cheap: a CSS filter on the dots, with no redraw. |
| **Svar i nyhederne** | Not a separate function: it is part of the answer reader (3.8). |
| **Hele biblioteket offline** | Folded into Gem (5.1) as its idle prefetch. |

---

## 6. Owner's calls (decisions this plan needs from him)

1. **Text selection.** On 11/10 the owner chose 'no text selection anywhere', so an app never pops a menu. The audits
   point out that this blocks quoting a sentence of a summary, an answer's 'Svaret kort' or a wiki lead, which is the
   core da'wah use.
   - My recommendation: allow selection only in reading text (`.sum`, `.ht-box`, `.rd-text`, `.wk-lead`, the wiki
     readings, `.quote`, the timeline texts).
   - Keep it off on rows, buttons and bars, and keep the long-press admin on rows.
2. **Pinch zoom.** It is off by the owner's choice ('an app, not a web page'). My recommendation: keep it off, and let
   the text size reach the bar, tabs and sheet (2.1). That covers most of WCAG 1.4.4 without changing his choice.
3. **The Topnyhed ration** of 5 a day and 12 hours (2.4). The numbers are his to tune.
4. **Moving Energi** out of Settings into the front page's foot and into oil stories (3.2, 3.4, 3.11).
5. **The share texts' ending** becomes 'via khabar.nu/?item=…' (or ?svar=, ?begreb=, ?forlob=), so the recipient
   lands in Khabar. The outlet's link stays in a story's share. The words 'via khabar.nu' stay last.
6. **Live filter and picture cards** (section 5, why the others wait).

Until he decides, the build does items 3–5 as described, and leaves 1, 2 and 6 as they are.

---

## 7. The build, in order

Each step is one commit (Conventional Commits, ending 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'),
bumps `?v=`, runs `py -m pytest -q tests` and `node --check`, and gets phone shots at 430 px, light and dark, text sizes
1 and 1.3. The steps marked ⚡ also rerun the round-2 measurements.

### Phase 1 – correctness and trust (what readers could misread or pass on wrongly)

1. **Share text.**
   - `shareText` uses the first sentence of `sumOf(i).text`. Otherwise it uses a cleaned teaser that shares at least
     two words with the headline, or no sentence at all.
   - Add the 'via khabar.nu/?item=<id>' ending, and a test that the shared sentence is the editor's.
2. **Teaser cleaning** in the app (`display()`/`detail()`) and in `feeds.tidy`: calls to action, URLs and mismatched
   teasers. Merge the two notes into the one credit line.
3. **Answers.**
   - The answer line moves under the main story in the package.
   - `detail()` skips the front page's `svarSet`.
4. **Timelines.**
   - One `stamp()` formatter.
   - Newest first everywhere, with day rows.
   - The package label names its development, and `threadFor` is the fallback, so the package and its button match.
   - The 'Udvikling: <name> ›' button.
   - The vocabulary: udvikling and opdatering, 'fulgt i N dage · senest …'.
5. **States.**
   - The offline and error block when `data` is null, and the skeleton at most 4 s.
   - Reload on `online` and `visibilitychange`.
   - `retry()` on the answer reader and the wiki page.
   - The not-found pages (`?item=` gone, unknown `?begreb=`).
   - The bar reads 'offline · …'.
6. **Deep links skip the intro** (the inline script), and `?forlob=` goes in `sideUrl`.
7. **Radar and editor** (section 4, items 1–5):
   - the push headline;
   - `kind: 'kommentar'`;
   - the `editor.py` checks;
   - the ÆNDRING strip;
   - the 'og' shortening in the reader.

   Tests for each.

### Phase 2 – the visual system (one coherent look)

8. **Type tokens** (2.1).
   - Map every font size onto the eight tokens, with `--ts` on `<html>` and `--ts-c` in the chrome.
   - A test: every `font-size` in style.css is a `var(--fs-*)` or on the exempt list. ⚡
9. **Two typefaces** (2.2): the lede, development names, quotes and the intro in the sans, plus the serif test.
10. **Colour discipline** (2.4):
    - no dot in `blockHead()`;
    - the lede date in `--text-3`;
    - section dots in search;
    - the Live label not red;
    - the Topnyhed ration in `meta()`;
    - the new-dot by the time;
    - the lighter day pill;
    - the dark segment fix;
    - a contrast test over the 8 palettes.
11. **Rows that keep their words** (2.6):
    - top alignment and the 4-line clamp with `contain-intrinsic-size: auto`;
    - meta items that wrap, never cut the outlet and never start with '·';
    - `tag: false` in single-section lists. ⚡
12. **Spacing, radii, separators** (2.3), and the `.grp` group header for search, A–Å and settings. ⚡
13. **Components:**
    - one `blockHead(title, more)` with a right-aligned link;
    - one quiet 'Vis flere';
    - the mini, chip, segment and jump sizes to 44 pt;
    - the icon sprite additions, with the CSS glyphs replaced.

### Phase 3 – the views

14. **Forside** (3.2):
    - the lede at three lines, tapping to Udvikling;
    - the Live block with `display()` titles and no commentary;
    - the energy row at the foot;
    - the fixed page's Danmark block.
15. **Live and the opened story** (3.3, 3.4):
    - the Kommentar label;
    - the outlet-prefix rule;
    - the wiki chips;
    - the oil row;
    - the bookmark square, at first only as space in the row, filled in step 22.
16. **Udvikling** (3.5): the share per card, the folded long course with its sticky name line, 'Resumé kl. …'.
17. **Analyser** (3.7):
    - the compact title;
    - the sticky strip with area and year chips and Begreber A–Å;
    - the topic row and 'via …' in search;
    - dimmed visited rows;
    - rows as links. ⚡
18. **The answer reader** (3.8):
    - the byline with Originalen;
    - the action row with share;
    - the 'Nyeste svar om …' strip;
    - 'Senere svar, der henviser hertil';
    - 'I nyhederne nu'.
19. **The wiki page and A–Å** (3.9, 3.10):
    - on the page: the contents row, the paired pages, news under the lead, the de-duplicated timeline, date-label
      rows and headings;
    - in A–Å: the sticky letters, the kind filter, the most-used chips and the nested issues.
20. **Bar, tabs, settings, intro** (3.1, 3.11):
    - in the bar: the refresh glyph and the back icon;
    - on the tabs: Analyser stays selected on its side pages, and a tap on the selected tab goes to the top or pops to
      root;
    - settings regrouped, with Energi under Mere;
    - the intro's three lines;
    - the iPhone install hint.
21. **Accessibility** (3.12): tab panels and `aria-hidden`, row labels, headings, the spoken new-story count. Then the
    VoiceOver check on the owner's iPhone. ⚡

### Phase 4 – the new functions

22. **Gem** (5.1): the side page 'Gemt', snapshots, the idle prefetch of the library, and the settings hint line. ⚡
23. **One search** (5.2): scopes, the Svar group, Danish suggestions, recent searches, collapsed 'Andre nyheder'.
24. **Mens du var væk** (5.3).
25. **Del dagens overblik** (5.4).
26. **Notifikationer efter eget valg** (5.5), including the radar's push changes and `push-test.yml`.

### Finally

27. **The round-2 measurement table, rerun in full**, before and after, appended to `notes-r2-speed.md`. Speed must not
    regress anywhere.
28. **The paperwork:**
    - CLAUDE.md, the app conventions: the two voices, red, tokens, states, vocabulary and the new functions;
    - CHANGELOG `[Unreleased]`, `.project.json` and README;
    - a plain-language note to the owner, with 2-up before/after phone shots of Forside, Live, an opened story, an
      answer, a wiki page and search, in light and dark.

**What the owner sees after Phase 1 and 2**, the first deliverable to show him:

- red only where something is big or live;
- headlines and outlets whole at every text size;
- the lede and the movement's text told apart by their type;
- timelines that say which day;
- a share that sends what he sees;
- an app that says so when it is offline.

Phases 3 and 4 then add the views' refinements and the five functions.
