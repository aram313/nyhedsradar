# The owner's rule on the front page (2026-10-17)

> "Forsiden skal laves og designes fra redaktørens egen smag."

**The rule:** the front page is not a fixed template the app fills. The editor (Claude) composes it at each update, by
its own editorial taste and the brain (the books' order of importance, the amir's newest readings): which blocks there
are, in what order, how many stories each holds, what leads, what a block is called. The app draws the editor's
composition with the app's own building blocks in khabar.nu's look (compact, text-first, minimal colour) – the editor
chooses the arrangement, never colours or fonts. No analysis: every word the editor writes on the front page is reality
(the lede, block titles, one-line captions), never a reading or judgement of its own.

**Data (digest branch, written by `editor.py publish`):** `front.json` =

```json
{"updated": "<iso>", "lede": "<the editor's sentence, as today>",
 "blocks": [
   {"kind": "top",       "story": "<id>", "title": "<informative headline>", "with": ["<id>"], "timeline": "<recap topic>", "picture": true},
   {"kind": "liste",     "title": "<block title, e.g. 'Krigen i Sudan' or 'Danmark'>", "stories": ["<id>"], "style": "kompakt" | "billeder"},
   {"kind": "udvikling", "topics": ["<recap topic name>"]},
   {"kind": "citat",     "quote": "<quote id from the update's quotes>"},
   {"kind": "svar",      "nr": "<an answer nr of the amir that bears on today>"},
   {"kind": "live",      "n": 3},
   {"kind": "linje",     "text": "<one short line of reality, e.g. a count: '14 nye angreb på Riyadh i dag'>"}
 ]}
```

- At most about 8 blocks (the app draws six since 17/10); a story appears in one block only; ids match a story's `id`
  or `members`. A list shows three stories, the rest behind 'Alle ›'; an all-Danish list of no weight two, last.
- `top` may appear once or twice (a day with two main stories); Dagens historie shows its picture (17/10), `picture`
  false gives a second main story a text lead. The lede may carry `lede_ids` (one story id per part).
- Unknown kinds and missing stories are skipped; if `front.json` is missing, invalid or older than 6 hours between 06
  and 24, the app falls back to today's fixed front page (lede, Dagens historie, Døgnets vigtigste, Følg udviklingen,
  Dagens citat, Live).

**The app:** renders the blocks in order with its existing components (the hero/Dagens historie card with its timeline,
compact rows with the small thumbnails, Følg udviklingen rows, the quote card, the 'Hizb ut-Tahrirs svar' row, the Live
preview), so the editor composes and the app keeps the look.

**The editor's input** shows the current composition and the palette above with a short guide (the owner's taste:
compact, few kinds of information per row, overskuelighed før fuldstændighed, block titles that never look like day
markers; Danish politics never buried); the update may send a new `front` or keep the current one.
