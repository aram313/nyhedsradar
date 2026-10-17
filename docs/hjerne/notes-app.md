# Notes – the app: Forside · Live · Analyser, the wiki and the amir's answers

Part of the hjerne branch (2026-10-17). The owner's decision: the brain weighs and selects the news only; the app shows
no analysis by Claude or Khabar; one Live section; a front page the editor makes; concepts named in the news open a wiki
page compiled only from the amir's political answers; the look stays as khabar.nu. Files: `public/app.js`,
`public/style.css`, `public/index.html`, `public/manifest.webmanifest`, `.github/workflows/pages.yml`, `.gitignore`,
`tests/test_app.py`. `public/sw.js` needed no change. Version `?v=20261017j`.

## What the app does now

**Three tabs** – Forside · Live · Analyser, in the tab bar's style (Analyser has a new open-book icon in the same line
style). The tab bar's grid takes as many columns as there are buttons, so a fourth (live world data, another session)
is a button, a page and an entry in `SWIPE_TABS`. The Danmark, Mellemøsten and Verden pages are gone with their code
(the lead/duo/panel cards, 'N mere fra døgnet', the section colours of a page). Live is every story of all sections,
'Seneste' or 'Vigtigste' as before, each row with its small section dot. The owner's long-press 'move' still sets the dot
(and the radar's Danish lift). Old links open Live: `?tab=dk|me|world`, a notification's `?item=` (the story opened in
Live, its headline just below the day band), the manifest's shortcuts (now Live, Analyser, Udvikling). New links:
`?tab=analyses`, `?begreb=<id>`, `?svar=<nr>`.

**Side pages over the tabs** (like Udvikling, the logo with its back mark): Udvikling, an answer (`svar`), a wiki page
(`begreb`) and the wiki's index (`begreber`). The logo goes back the way one came – Forside → a story's concept → its
answer → back → back – with each page's scroll position kept; a tab starts the way afresh.

**The front page** is today's: the lede, Dagens historie, the top stories, Følg udviklingen, Dagens citat, Live – plus one
quiet line under Dagens historie when the amir has answered on the main story's subject: »Hizb ut-Tahrirs svar · d/m/åååå«
over the Danish title (whose and when on the first row, so a long title or text size 1.3 never cuts the date), opening
the answer reader. An opened story shows the same kind of line between its actions and its small buttons (not for the
main story, whose line is the package's).

**Which answer** (`answerFor`): a story names subjects in its headline, the radar's `actors` and the recap topic's name
(weight 1) and in its summary (½). An answer is about the subjects its Danish title names, the first one its question
names, its main issue (and its first state when that is the issue); the rest of its question it only touches. It
qualifies when a headline subject that is not in nearly every answer (idf > 0.5, so not the USA) is one it is about, a
second signal agrees (another shared subject – a broad one only from the answer's title – or two shared words of its
title and question, generic words and Trump/Putin left out), and it is at most three years old (a current reading
governs). The best of specificity × recency wins (a year older weighs about a third); else no line. Measured on the 60
top stories of 16/10 (the radar agent's preview): 21 get a line, all on their subject – the Iran war stories the answers
of 28/6 and 3/6/2026, every Houthi story the Yemen answer of 27/9/2026, the Russia/Ukraine stories that of 12/6/2026,
the Israeli army in Lebanon that of 2/5/2026, Gaza killings 'Fordrivelsen af Gazas befolkning' (28/1/2025). Two looser
versions were tried and dropped: by the layer's subject lists alone, 14 Israel/Palestine stories got 'USA's nationale
sikkerhedsstrategi' (its only listed state is Israel); with every subject a question names, a China–Israel settlements
story got an Indonesia answer.

**The wiki's names in the text** (`linker`, `scan`): `viden/begreber-index.json` (30 KB, 6 KB gzipped) loads at the
start; every page's aliases and, but for an issue, its name, as two patterns (case kept / not), the longest form first,
whole words with a possessive (s, 's, ’s, ') – the rule of `build_begreber.name_pattern`. Not linked: Danmark (in every
Danish story, a page of one answer), and anything inside an outlet's name (the sources' labels and 'Jerusalem Post',
'Times of Israel' …). Linked where the text is plain: the lede, an opened story's headline and summary (one block), the
recap lines on Udvikling and in its earlier days (a topic or a development is one block), the front page's timeline,
an answer's 'Svaret kort'. The first mention of each page, at most three a block, a quiet dotted underline in the text's
colour. **Never inside a button or link:** a story row, a recap line and a timeline step keep their button or link
under the whole row, the words lie on top with `pointer-events: none` and let the tap through, the names are real links
on top (`a.bg`); checked with `elementFromPoint` – a tap on the words reaches the row's button, on a name the link. A
closed row's links are inert and invisible, so a tap anywhere opens it.

**A wiki page** (`begreb`): kind and number of answers, the name; the lead in the movement's face with 'Svaret af
d/m/åååå: <title>' to the answer it rests on; 'Gennem årene' (the timeline by year, newest first, five then 'Hele
forløbet · N'; each row opens its answer); for states and powers 'Forhold' (each party's page tappable); 'Svar om
emnet' (six, then all); 'Relaterede begreber' (chips, ten then '+ N'); 'I nyhederne nu' (the last 24 hours' stories that
name it – by the radar's actors or the linker –, quiet grey, a tap opens the story in Live). The editor's new answers
(answers.json, after the static 321) join the pages they name at once: their readings lead the timeline and they lead
the answers, until the next build of the wiki takes them in.

**Analyser**: »Hizb ut-Tahrirs svar på politiske spørgsmål – Nyeste først · 321 svar fra 2004 til 2026«, a search field
(titles, questions, the names of the pages each answer reads – and, once the whole wiki is here, the concepts too) and a
quiet 'Begreber' row to the A–Å index (203 pages by letter, each with kind and answers). Then 'Nye svar' (the editor's
filed answers and the radar's `analyses` not yet in the layer; a found one not yet filed shows its original title and
'endnu kun på engelsk'), then the layer's answers by year under day-marker bands. A row: the Danish title in the serif,
one line 'd/m/åååå · area' (the first issue's name). A new answer puts a dot on the tab until the phone has seen it
there. The search field keeps its keyboard: only the list is drawn again; Analyser and the index are not redrawn at a
news reload unless what they show changed.

**The answer reader** (`svar`): 'Hizb ut-Tahrirs svar af d/m/åååå · area', the Danish title (the original small, where
it is known – the layer holds no original titles, so only the radar's new answers have one), 'Spørgsmålet', 'Svaret
kort' (note_da, with the wiki's names), 'Hvad svaret læser' (its readings grouped by subject, each subject's page a
link; inside the answer's own page its own date's attribution reads 'Ifølge svaret …', a span over other answers keeps
its full attribution), 'Begreber i svaret' (chips), 'Svaret henviser til' (the answers it cites), the English text when
held (`analyses.json` on the data branch: the radar keeps only answers the layer lacks; each paragraph finds its own
direction – the text opens with the Arabic basmala) and 'Åbn originalen'. movement.json (225 KB gzipped) and
begreber.json (241 KB gzipped) load when the first answer or wiki page opens, then stay.

**The movement's face**: everything that is Hizb ut-Tahrir's – a page's lead, timeline and relations, an answer's
question, note, readings and text, the answer lines – in `ui-serif, "New York", "Iowan Old Style", Charter, Georgia`
on a soft ochre tint, always with its attribution; everything else unchanged. Light `#efe7d6` (Papir `#e6d7b7`, the paper
itself being ochre), dark `#2a251d`; text 12.2:1 / 12.0:1, secondary 6.3:1 / 8.4:1, labels 5.1:1 / 5.8:1 (all ≥ 4.5).
Every new font size is `calc(Npx * var(--ts, 1))` (the Analyser field `max(16px, …)` so iPhone never zooms).

**Also**: the coverage view and the sources list name the radar's new groups – 'Russiske, kinesiske og indiske medier',
'Regeringers egne kanaler', 'Bevægelsens egne kanaler' (they were silently left out). Search shows the wiki pages its
words name (from three letters) as ochre chips (so they are not taken for the word completions above them). The 'new stories' pill shows only on Forside and Live.
`pages.yml` writes `answersUrl` (digest branch) and `analysesUrl` (data branch) beside `energyUrl`.

## Measured (headless Edge, 430 px at 2x, text size 1.3, light and dark; a fast PC, no throttling)

- DOM after start 5,342 elements (the performance note measured 12,910 with five tab pages). Drawing: Forside 6 ms,
  Live 30 ms, Analyser 1.4 ms, Udvikling 7.5 ms, the index 1.2 ms; `answerFor` 0.05 ms a story; the linker over all 684
  headlines 1 ms.
- app.js 165 KB (54 KB gzipped), style.css 73 KB (16 KB). Wiki files: index 6 KB, movement-index 46 KB, movement.json
  225 KB, begreber.json 241 KB gzipped.
- Walked: Forside → Dagens historie → a name in it → its page → the lead's answer → back → back (scroll kept); Live
  (a story with its links and answer line); Analyser → search 'houthi' (12 answers) → an answer → back (the query kept);
  Begreber A–Å → Houthierne; Udvikling (17 links over its cards); `?tab=dk|world`, `?item=`, `?digest=1`,
  `?begreb=nato`, `?svar=28942`; settings (the eight groups). No JS errors; the only console lines are 404s for
  `favicon.ico` and the not yet existing `answers.json` (the app takes that quietly and asks again after ten minutes).
- A new answer's whole path with real content (`?dev=new`, below): the tab's dot, 'Nye svar', the reader with the
  editor's readings and the English text, the dot gone after a visit.
- Screenshots: `…\scratchpad\hjerne\final\{light,dark}-{1-forside … 9-udvikling}.png`. The brief's plain CLI flags
  (`--window-size=430,932 --screenshot`) lay the page out wider than 430 px (Edge's minimum window width) and cut the
  right edge, so the shots use the same headless Edge through the DevTools protocol with an exact 430 px viewport.

## Preview on today's data

`public/config.js` (gitignored) points at `public/dev/` (gitignored, added to .gitignore): the radar agent's
`.cache/hjerne-preview` data.json and lines.json, and digest/summaries/moves from `origin/digest`, search.json from
`origin/data`; pictures from the live data branch. `?dev=new` loads `public/dev/new/`: the movement's answer of
27/9/2026 as a new answer – removed from a copy of the layer, filed in answers.json from the layer's own Danish
readings, listed in data.json's `analyses` with its English text (the local archive's copy) in analyses.json – the path
a real new answer takes before the next build. Serve with `py -m http.server 8791 --bind 127.0.0.1 --directory public`.

## Open points

- The front page and opened stories get their answer line from the layer's index and the editor's answers.json; the
  concept pages' own answer lists (in begreber.json) are not used there, to keep 241 KB off the start. A story that names
  only a concept ('Vestbredden', 'normalisering') therefore gets a line only through a state or issue it also names.
- The layer has no original (English) titles; the reader shows one only for the radar's new answers. build_movement.py
  could carry them (the local corpus has them).
- `answers.json` does not exist on the digest branch until the editor files the first new answer: until then every phone
  asks for it at most every ten minutes and gets a 404 (harmless, one line in the console).
- The wiki's leads, timelines and relations are not linked to other pages inside their text (only the answer's note is,
  as the brief says); the related pages and the relations' parties are.
- The owner's newer note `notes-owner-front.md` (the editor composes the front page block by block in `front.json`, the
  app draws it with its own components, today's page as the fallback) came after this brief and is not built; the
  pieces it names exist (the hero with its timeline, compact rows, Følg udviklingen, the quote card, the answer line,
  the Live preview).
- The performance pass (notes-owner-performance.md) still applies: Live redraws whole on a reload, and the first answer
  opened costs about 470 KB gzipped of the wiki and the layer; splitting movement.json per answer would cut that.
