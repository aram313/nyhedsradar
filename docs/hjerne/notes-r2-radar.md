# Round 2 – the radar: the sources' fit, headline rules, Live's level and app.json (2026-10-17)

Part of the hjerne branch, round 2 (the owner's rules of 17 October: notes-owner-sources.md, kilder-maaling.md,
notes-owner-volume.md as revised, notes-owner-headlines.md). Files: `src/radar/run.py`, `src/radar/feeds.py`,
`src/radar/headlines.py` (new), `src/radar/level.py` (new), `src/radar/sections.py`, `config/feeds.json`,
`config/sections.json`, `config/settings.json`, `scripts/rank_check.py`, `.github/workflows/radar.yml`, tests
`test_level.py`, `test_headlines.py`, `test_fit.py` (new) and `test_run.py` (one test isolated from the fit).

All numbers below are one radar pass on the same copy of the live data branch (17/10 08:20 Danish time, 7,984 kept
items, the 62 sources main runs; the 31 + new sources of this branch had no data yet), before and after, with
`RANK_CHECK_STATE` – and, for the level, 17 + 9 + 9 passes going back over 15–17 October.

## 1. The sources' fit (config/feeds.json `fit`, 0.5–1.3)

**Which outlet leads a story** (`lead_quality` in run.py). The hard order stays: a Danish or English article first,
never the movement's outlets, governments' channels, sources added for their camp (`scale: false`) or unverified
channels while an established outlet carries the story. Among the rest:

    fit  + 0.35 for a Danish headline  + 0.1 with a teaser  + taste/1000  − 0.5 for a curiosity headline

- The Danish bonus (`lead_danish`) is my choice: until the editor has written his own headline the app shows the lead's
  headline in Danish, and a Danish outlet's own words read far better than the machine's translation of an English one
  (the first trial without it gave "BT: Kraftigt jordskælv har ramt Rusland" to Anadolu in English, Ekstra Bladet's
  Norwegian murder plot to Al-Monitor). A curiosity headline still loses to an informative English one of fit ≥ 0.85.
- **Curiosity headlines** (`src/radar/headlines.py`, `curious(title)`): a question (also "Kan Europa stole på USA?
  Mette Frederiksen tøver"), "Derfor/Se/Her er/Sådan/Hvorfor …", "Why/How/What/Explainer …", tabloid labels ("Klamt
  fund:"), "What we know", "– and why", "- opinion/- analysis" at the end, a first line that only names who speaks, a
  quotation with no one named after it. Danish and English only. Measured on the snapshot: DW 23 %, Times of Israel
  19 %, JPost 18 %, BBC 18 %, Politiken 10 %, Reuters 4 %, DR 0 % (lower than kilder-maaling.md for the tabloids: the
  rule leaves cliff-hanger colons alone, so "Kremlin: …" and "Mette Frederiksen: …" never count – rather too few than a
  speaker's statement counted as a teaser). The editor's tools may use the same function to find the admitted stories
  that most need an informative headline.

Measured: of 118 stories with several outlets, **49 change lead** – 35 to an outlet of better fit (BT → DR on Moldova,
Ekstra Bladet → DR on the White House spokeswoman, Ekstra Bladet → Altinget on the Lidegaard verdict, Times of
Israel → Middle East Eye on Aden), 5 from a curiosity headline to an informative one (Reuters "How are Yemen's Houthis
attacking Saudi Arabia so effectively?" → NYT, JPost's "- opinion" → Anadolu, Politiken's bare quotation →
Berlingske), 9 by teaser or taste. **Curiosity headlines leading a story with several outlets: 8 → 1** (the one left:
5Pillars and DW both ask "Why is Azerbaijan banning the hijab?"); in the whole pool 52 → 33. The method's tier reads
the lead's headline, so an informative lead can also place a story better: the 12-outlet story led by BT's "Putins
toprådgiver jubler over Trump" (tier 5, rank 126) is now JP's "Trump suspenderer nye sanktioner og told mod Rusland"
(tier 1, rank 136, first in Live).

**In the rank**: `rank_fit` × (lead's fit − 1), `rank_fit` = 10, so −5 (fit 0.5) … +3 (1.3). On the snapshot: −4 for 2
stories, −3 for 10, −2 for 22, −1.5 for 91, −1 for 92, −0.5 for 49, 0 for 161, +0.5 for 29, +1 for 21, +1.5 for 127,
+2 for 70. Small beside the taste percentile, the outlet lift (4 per outlet) and the Danish lift (18). The Danish lift
and the dk rules are untouched. Each story in data.json carries its lead's `fit`.

Top of Live (the last 24 hours by rank) before → after: 7 of the top 10, 21 of the top 25 and 39 of the top 45 are
the same stories. New in the top 45: the Berlingske story on the Muslim influencer and Pia Kjærsgaard (tier 6, four
outlets, now one story), the Houthi attacks on Saudi Arabia (NYT leads instead of Reuters' question), the Oregon school
shooting (DR leads, 12 outlets), Anadolu on the Security Council and the Houthis, a QudsN raid in Silwan and JPost's
report on Netanyahu before 7 October. Out of the top 45: JPost's opinion piece (filtered now), Clash Report's bare
"Denmark's PM Mette Frederiksen on Russia:" (now joined to what she said, ranked lower by fit 0.85), and the stories
at 103–106 that the level's line now cuts (below).

## 2. The headline rules at intake (`feeds.tidy`, per source in feeds.json `drop` / `cut`)

Applied to every fetched item and once to every kept item (so the state is clean at the first pass; a second pass
changes nothing). Per source in feeds.json (regular expressions, case-insensitive; the caretaker's format is kept):

| Source | Rule | On the snapshot / a live fetch |
|---|---|---|
| Times of Israel | drop `^The Blogs:` | 56 of 358 items |
| Jerusalem Post | drop ` - opinion / analysis / comment / editorial / op-ed` at the end | 38 of 230 |
| BT | drop `Expekt`, `Bet Builder` | 14 of 519 |
| Ahram Online | drop ` - Sports / Advertising / Opinion` at the end; cut the section tail (" - Foreign Affairs - Egypt") | 9 dropped, 13 cut of 24 |
| Shafaq News | cut the prefix `Shafaq News..` | 36 of 38 |

For every source of a kind:

- **Google News** – after its own " - Outlet": a tail after `»` ("» Iraqi News Agency", 37 of INA's 49), and a tail
  after `|`, ` - `, `–`, `_` that is the site's name or slogan (shares a word with the source's name/label, or says
  news/agency/latest/breaking/online: "- Enab Baladi", "- The Jordan News Agency", "| Latest breaking news in Iraq and
  the world", "- Latest news, videos and opinion"). "Gaza: 340 children killed … - UNICEF" keeps its source. Hub pages
  that become "Israel", "Home", "Search" are left out by the radar's 4-word rule.
- **Telegram** – a first line that only names who speaks ("Palantir CTO Shyam Sankar:", "Kamala Harris on Israel:",
  "Azerbaycan milletvekili Agil Abbas:") becomes that and the first sentence of what was said (68 Clash Report posts,
  8 Daily Islamist, 1 DOAM, 2 Warfare Analysis, 13 Quds News Arabic).
- **Language per post** (`feeds.sniff`): a post of an English channel is Turkish when its Turkish words and letters
  outnumber its English words more than twice (Turkish function words – ve, bir, ile, için, gibi, değil … – count, not
  only ğ ı ş İ). 8 of Daily Islamist's 30 kept posts were filed as English and are Turkish now (they are translated
  from Turkish, and their old machine Danish is dropped); "Türkiye's Erdoğan meets Putin in İstanbul" stays English.

## 3. Live's level (`src/radar/level.py`, settings `live_levels`, `live_keep_margin`)

`radar.yml` reads `live.json` from the digest branch beside digest.json (`.cache/live.json`, `RADAR_LIVE`; removed
before the cache is saved). The plan: today's Danish date's `level`; no file, no entry for today, an unknown level, or
`updated` more than 2 hours old between 06 and 24 → `normal` (`why` says which). `take` and `drop` of every day the
file keeps apply whatever the level's state (they are decisions about single stories); drop wins over everything,
even a big story; an id matches a story's `id` or one of its `members`.

Each level is a rank floor and a soft count for the last 24 hours (by `published`, else `found` – the app's own clock):

| level | floor | count | admitted in 24 h (passes 15/10 08:00 – 17/10 08:00 Danish time, every 3 h for normal, 6 h for the others) |
|---|---|---|---|
| få | 104 | 20 | 30–40 |
| normal | 96 | 38 | 43–56 (median 50) |
| mange | 88 | 72 | 75–86 |

The pass goes down the stories by rank: take, a protected story or – while fewer than `count` are admitted and the
rank reaches the floor – the next by rank comes in; a story admitted on an earlier pass stays while its rank is within
`live_keep_margin` (4) of the line (the floor, or the rank of the last story the count let in), so Live does not flicker
when a stronger story arrives. A story the day's pass leaves out is forgotten (state/admitted.json keeps the members of
admitted stories), and a story older than 24 hours keeps the admission it had (up to 48 hours: the app's window); the
very first pass, with no record, decides the day before by the same rule.

- **Never cut** (`protect`): every big story, and a confirmed Danish story (section dk, not light news) on Islam and
  Muslims, integration and immigration, or foreign policy – tier 6, or a word of the new `protect_dk` list in
  config/sections.json in a Danish member's headline (muslim, islam, moské, tørklæde … udlænding, integration,
  statsborgerskab … udenrigs, Gaza, Israel, palæstin, Iran, Ukraine, Rusland, Trump, USA, Grønland, Nato, sanktion …).
  3–8 such Danish stories a day. Danish politics in general is not protected but keeps its lift (+18), so it mostly
  ranks above the line; local politics at 105 (TV 2 Øst, TV 2 Fyn) falls below it at normal.
- **Why the counts are lower than the owner's example (25/45/80):** the protected stories count too (Live's real
  size), and these days had 14–24 big stories in 24 hours (the Houthi attacks on Saudi Arabia, the West Bank, Russia).
  `få` therefore cannot go below the big stories: 30–40 on these days, of which only 6–12 come in by rank alone. On a
  quieter day the floors bind and Live is smaller (a quiet day is never padded). The counts 38 and 72 give normal and
  mange about 45–55 and 75–85; the margin 4 keeps 'kept' stories at 2–10 (with margin 6 and the first counts it was up
  to 15, and normal reached 66).
- At normal on the snapshot: 46 of 196 candidates (17 big, 5 Danish, 24 by rank), line 107.5; the strongest left out:
  three QudsN posts (106.5), Reuters on Russia's refinery claims (106.5), DR on Moldova (106).
- Notifications go only to stories Live shows (`live` set); before, any candidate of the pool could be notified.

## 4. app.json beside data.json (data branch)

`app.json` = the admitted stories of the last 48 hours plus every big story in the pool, with only what public/app.js
reads. On the snapshot at normal: **168 KB, 88 stories – against data.json 979 KB, 674 stories** (gzip: 62 KB against
291 KB; at få 126 KB / 57, at mange 236 KB / 149). data.json stays the whole candidate pool (the editor, search).

For the app agent – the shape of app.json:

- top level: `updated`, `sections`, `scanned_24h`, `analyses`, `owner` (as in data.json), `sources`
  (`{name: {label, group, failing_runs only when > 0}}`), `live` (`{level, n_24h}`), `items`. No `learned`.
- an item: `id, title, summary, link, source (the label), group, lang, published, found, rank, sec, secs, big, important,
  outlets, confirmed, cover, foreign, title_tr, summary_tr, title_da, summary_da, thumb, pic, kw, kw_tr, kw_da, actors,
  members, live, also`. **Empty values are left out** (None, '', [], {}, false): read a missing field as empty;
  `confirmed: 0` stays. `members` is left out for a story of one article: use `i.members || [i.id]` when matching the
  editor's ids (front.json). `pct`, `spct`, `camps`, `first`, `tier`, `tags`, `powers`, `method`, `fit` are not in it.
- `also` entries: `id, source, title, link, lang, group, title_tr` (no `published`, `camp`).
- `live` on an item says why Live shows it: `rank`, `kept`, `big`, `dk`, `take` (a big story older than 48 hours has
  none). The app must not show this word; it is for the editor and for tests.
- `pages.yml` needs an `appUrl` (…/data/app.json) in config.js, and the app falls back to data.json without it.

## 5. What the editor's input gets from the rank line (for the editor agent)

In **data.json** (the pool the editor reads):

- top-level `live`: `{level, why ('redaktøren' | 'ingen live.json' | 'ingen plan for i dag' | 'ukendt niveau' |
  'forældet'), note, plan_updated, floor, count, margin, line, n_24h, n_48h, by_why_24h, candidates_24h, take, drop}` –
  the level applied, today's count and the line (the rank of the last story the count let in, or the floor when the
  count did not bind).
- each item: `live` (why it is admitted, or null), `rank`, `fit` (the lead's), `members`, `first`, `tier` as before.
- *Just above / below the line*: the items of the last 24 hours (`published || found`) sorted by `rank`; admitted =
  `live` not null. Above the line with `live: kept` or a protected reason are those the count would not have let in.
- *Admitted and waiting for an informative headline*: `live` not null and no editor title in summaries.json `titles`
  (by id or a member); `radar.headlines.curious(title)` marks the ones whose own headline is a teaser.
- The update's `level`/`take`/`drop`/`note` go to live.json as notes-owner-volume.md describes; the radar applies them on
  its next pass (within five minutes). A `take` only reaches stories in the pool (data.json); a story below the taste
  bar is not there to take.

## Tuning and checks

- `py scripts/rank_check.py` now prints Live's level, the line, the admitted count and why, app.json's size against
  data.json, the admitted stories by rank and the strongest left out. `RANK_CHECK_LEVEL=få|normal|mange` tries a level
  as if the editor had just set it; it reads the digest branch's live.json (or the saved state's) otherwise.
- Settings: `rank_fit` 10, `lead_curious` 0.5, `lead_danish` 0.35, `live_levels` {få: [104, 20], normal: [96, 38],
  mange: [88, 72]}, `live_keep_margin` 4.
- Tests: 184 pass (`py -m pytest -q tests`). test_run's trust/balance test sets `rank_fit` 0 for itself: with three
  stories of equal taste in one section the fit alone decides which reaches the section's top 15 %, which is not what
  that test is about.

## Open

- The counts were tuned on two heavy days (14–24 big stories); a quiet day will show whether `få` is quiet enough –
  rerun the level passes on a quiet day's snapshot.
- The new sources of this branch (Ahram, Shafaq, INA, Petra, Enab Baladi …) were checked on one live fetch, not on
  days of data; their rules should be looked at again once they run.
- Whether 'big' should become stricter is not this round's question, but it now decides most of `få`.
