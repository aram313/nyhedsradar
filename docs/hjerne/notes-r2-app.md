# Round 2 – the app: app.json, the editor's headlines, the composed front page (2026-10-17)

Part of the hjerne branch, round 2 (the owner's rules of 17 October: notes-owner-headlines.md, notes-owner-volume.md as
revised, notes-owner-front.md). Files: `public/app.js`, `public/style.css`, `public/index.html` (`?v=20261017m`, one
hint), `.github/workflows/pages.yml`. Built on the radar's `app.json` (notes-r2-radar.md §4) and the editor's
`summaries.json` titles and `front.json` (notes-r2-editor.md).

## What was built

**Loading.** `load()` asks for the news, digest.json, summaries.json and front.json side by side (`Promise.allSettled`;
before, one after another). The news are `CFG.appUrl` (app.json: the stories Live admits, 163 KB / 87 stories on
17/10 09:05 against data.json's 975 KB / 672); when app.json is missing or fails, `CFG.dataUrl` (data.json) as before.
Live, the front page's pool and the stories found from the wiki and the recap all read that one list; search still
covers every story (search.json). A front.json that answers 404 means 'no composition' (the fixed front page); a failed
request keeps the last one. `pages.yml` writes `appUrl` and `frontUrl` into config.js (the app derives both if absent:
no appUrl → data.json, no frontUrl → front.json next to digest.json; energyUrl is unchanged).

**Headlines** (`display()`). In this order:

1. The editor's headline (summaries.json `titles[id] = {title, at, members}`): it is indexed under the story's id
   **and every member**, the newest one winning, and a card finds it by its id, its `members` or its other outlets'
   ids – so it still applies when another outlet's article leads the card. It is shown for Danish stories always and
   for foreign ones while 'Vis og del på dansk' is on (the standard); 'Original' for Arabic/Turkish keeps the outlet's.
2. Else the outlet's headline – the machine's Danish where the phone shows Danish, as before.
3. Where that outlet headline is a plain curiosity headline, the first sentence of the teaser instead (in the language
   shown, else the outlet's own teaser), a wire's dateline ('… (Reuters) - ') left out, shortened at a word boundary to
   at most 120 characters ('…' when cut). The teaser's sentence is not shown twice: the summary below starts after it.
   No teaser, or a teaser whose first sentence is itself a teaser, too short or not a sentence: the headline stays.

The curiosity test is the radar's own (`src/radar/headlines.py` `curious`), ported to `curious()` in app.js; on all 952
headlines of the 17/10 pool the two agree on every one (53 curious). On that pool with the editor's titles of a local
publish: 45 of 87 stories carry the editor's headline, 14 the machine's Danish, 27 the outlet's own, 1 the teaser's
sentence ('Se videoen: 'Terrorhyldest' til stor demonstration' → 'I København bød weekenden på en pro-palæstinensisk
demonstration'). Two curiosity headlines have no teaser to stand in ('Kan Europa stole på USA? Mette Frederiksen tøver',
Reuters' 'How are Yemen's Houthis …'): they wait for the editor.

**The opened story names the original** (`origNote`): 'Originaloverskrift: »…«' (with 'på engelsk' etc. for a foreign
one) where the shown headline is the editor's or the teaser's; 'Maskinoversat fra engelsk · original: »…«' for the
machine's Danish as before; nothing when the shown headline is the outlet's own. The old 'Oversat … og tjekket af
redaktøren' is gone (every headline is now the editor's). The settings' hint under 'Vis og del på dansk' says
'Overskrifterne vises på dansk – skrevet af redaktøren, ellers maskinoversat.' The app never names Claude.

**The front page** (`home()` → `composedHome()`, else `fixedHome()` – the old page unchanged). front.json is used when
it has at least one known block and its `updated` is under six hours old – or, between 00 and 06 Danish time, any age
(the evening's composition stays through the night; the editor does not keep an earlier day's after 06). An
unreadable date, no known block, or a composition whose stories have all left Live → the fixed page. The blocks, in
the editor's order, with the app's existing pieces:

| kind | drawn as |
|---|---|
| `top` | the 'Dagens historie' panel (its title only on the first `top`): the hero card with the editor's `title` (`picture: false` or no picture: a text lead – a larger headline row without the thumbnail), the `timeline` topic's last four steps ('Sådan udviklede det sig', matched by the recap topic's name over all days), the `with` stories as rows, and the amir's answer line on its subject unless a `svar` block names the same answer. The owner's held main story (data.json `owner.lead`) takes the first `top`'s place. |
| `liste` | a block with the editor's `title` and its stories as the usual rows with the small pictures; `billeder`: the first story with the outlet's own picture set large, the rest as rows |
| `udvikling` | the 'Følg udviklingen' rows of the named topics + 'Hele dagen og alle udviklinger' |
| `citat` | the 'Dagens citat' card (the quote is inline in the block; the owner's pinned quote wins) |
| `svar` | the ochre 'Hizb ut-Tahrirs svar · d/m/åååå' line to the answer reader (filled in when the answers come) |
| `live` | the Live strip with the `n` newest + 'Se alt i Live' |
| `linje` | one quiet line of the editor's text, with a thin rule at the left, wiki names linked |

A story appears once on the page (the first block that names it), an unknown kind or a story no longer in the pool is
left out, the lede is `front.lede` (else digest's), and the date and the 'Khabar har læst …' foot stay as before.

**Coverage and sources.** The groups east, official and bevægelsen are named in the coverage view ('Russiske, kinesiske
og indiske medier', 'Regeringers egne kanaler', 'Bevægelsens egne kanaler') and in the sources list in Indstillinger
(the labels were added in round 1; checked again here on app.json's `sources`, which carries `group` for all 123).

**A fix on the way.** An empty answer place (`.ans-ref:empty` has `display: none`) measured as standing at the top of
the screen, so filling it in scrolled the page by its height: with two or three such places the front page opened
184 px down, the date and the lede hidden. `fillIn()` now measures an empty place by what stands before it.

**pages.yml.** Besides the two URLs: its `sed` renamed `radar-shell-v1`, but sw.js says `radar-shell-v3`, so the
service worker's cache name never changed per deploy and old versioned files stayed on the phones; it now matches any
`radar-shell-vN`.

## Preview (local only)

`public/config.js` (gitignored) has `?dev=r2`: `public/dev/r2/` holds a `scripts/rank_check.py` pass of 17/10 09:05
(`RANK_CHECK_OUT`: app.json, data.json, lines.json) and the digest branch's files after a local
`py scripts/editor.py publish <update> --dir public/dev/r2 --out …` of a test update (11 headlines, one quote, an
8-block composition: top with picture, liste Danmark, top as text, udvikling, liste billeder, citat, svar 30420, live –
accepted by the editor's checks). `&front=0` shows the fixed page, `&app=0` reads data.json.

Checked at 430 × 932, 2x, headless Edge through the DevTools protocol: light and dark, text size 1 and 1.3 – the
composed front page from top to foot, the fixed page, Live (Vigtigste and Seneste), an opened story with the teaser's
sentence, one with the editor's headline over an English original, the coverage view with all eight groups, the
sources list. No console errors (only the expected 404 of a missing front.json/answers.json). `node --check` on app.js
and sw.js; `py -m pytest -q tests`: 184 passed, 5 skipped.

## Open

- The editor's headlines of before round 2 (its checked translations of the eight strongest foreign headlines) stay
  for their four days and are shown first like the new ones; a few are questions ('Hvorfor forbyder Aserbajdsjan hijab
  i skolerne?'). The app does not second-guess the editor; they age out by 21 October.
- Bold keywords: the radar's `kw` are the outlet's (or the machine translation's) words; the editor's own headline
  bolds only those it shares with them. A `kw` for the editor's headline (the editor or the radar marking who and where)
  would bring the bold back fully.
- notes-owner-performance.md (speed) is its own part: this round only made the reload's requests parallel and the
  stored news smaller (app.json instead of data.json in localStorage).
