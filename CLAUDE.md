# CLAUDE.md — Nyhedsradar

Project-specific instructions. The workspace-wide rules are in `E:\CLAUDE.md` and
`E:\STRUCTURE.md` and apply here too — this file only adds what is specific to this
project.

## What this project is

Telefon-app (Khabar) der automatisk finder og vejer nyheder til Debat/Nyheder Shabab-gruppen – én Live-liste, en forside fra redaktøren, Hizb ut-Tahrirs svar og en wiki over begreberne – med deling til WhatsApp og notifikationer

**The direction (the owner's decision of 2026-10-17, binding; it replaced the Khabar 2 app, branch `khabar2`, kept only
as a source):** the brain – the order of importance of Hizb ut-Tahrir's political books and the amir's political
answers, the newest answer governing older material – is used **only to select and weigh the news**: the radar's tiers
(`src/radar/method.py`) and the editor's front page (`scripts/brain.py`). The app shows **no analysis, judgement or
hypothesis by Claude or Khabar**; the editor's own text stays reality (lede, recap lines, summaries, titles). The amir's
answers appear only as his, in their own face, and **said once per block, in its label** ('Hizb ut-Tahrirs svar ·
d/m/åååå'; a block of several answers' texts dates each row) – never 'Ifølge Hizb ut-Tahrirs svar …' in the texts
themselves (the owner, 2026-10-17: "det står over det hele"). Concepts
named in the news open a wiki page compiled only from those answers. The site is looked at every quarter of an hour
("Claude skal køre hvert 15. minut … der er tokens nok"): the look is plain Python after every radar pass
(`editor.py gate`), and it fires Claude – the editor's routine – when something needs adjusting, within the
subscription's daily run cap (docs/hjerne/cadence.md). The users are young Danish Muslims who use the news in their
da'wah.

## Stack

- **Type:** `web-app`
- **Technologies:** python, github-actions, pwa

## Commands

<!-- Fill these in as soon as they exist. Exact, copy-pasteable, no placeholders. -->

| Task | Command |
|---|---|
| Install dependencies | Cloud only: `pip install -r requirements.txt` (runs in Actions; locally only numpy + pytest are needed) |
| Run in development | `py -m http.server 8765 --directory public` (with a local `public/config.js` pointing at copies in the gitignored `public/dev/`) |
| Run tests | `py -m pytest -q tests` |
| Build for production | Push to `main`; `pages.yml` publishes `public/` |
| Run the radar now | `gh workflow run radar.yml` |
| Rebuild the wiki | `py scripts/build_begreber.py` (after `scripts/build_movement.py`, and whenever `docs/hjerne/begreber-ideer.json` changes; commit both `public/viden/begreber*.json`) |
| Rebuild the movement layer | `py scripts/build_movement.py` (needs the local `.cache/movement` extracts and `docs/hjerne/qa-index.json`) |
| What the editor's quarter-hour look sees | `py scripts/editor.py check` |

## Architecture

- `src/radar/feeds.py` fetches and parses every source type (rss, gnews, telegram, youtube, sitemap). Stdlib only.
  `sitemap` (18/10, the owner: 'Axios og reuters burde være nogle primære kilder'): an outlet's own Google news sitemap
  where it has no feed (`parse_sitemap`: headline, time and picture of every article minutes after it is out; `pages`
  pages of `step` articles, `&from=…`; only the feed's language and the sections its `path` regex names) – 'Reuters
  direkte' (world, legal, investigations, energy, aerospace-defense, commodities; fit 1.15), listed before the two Google
  News searches on Reuters so its own headline wins the dedupe; those stay as the fallback. Axios comes from its own RSS
  (api.axios.com/feed/: every national story it publishes; its news sitemap adds only Axios Local and Pro).
- `src/radar/run.py` is one radar run: dedupe → embed → self-learn → score → cluster (+ second look at cards)
  → sections and rank (+ the lead by fit) → show/important/big → Live's level (level.py) → translate → notify → write
  state, `data.json`, `app.json` and `search.json`.
- `src/radar/sections.py` places stories in dk / me / world and gives the word signals (core, core_dk, trivia,
  local, named) used by the rank; the word lists live in `config/sections.json` (format explained in its `_help`).
  Every source in `config/feeds.json` has a media `group` (dk, west, mena, il, east, official, channel, bevægelsen), a
  `camp` (the state or bloc whose view it carries) and some a section hint `sec`;
  `label` is the readable name the app shows, `official` marks a news outlet's own Telegram channel (not an
  unverified channel) and `last` a source of last resort (Times of Israel, the owner 18/10: 'Brug kun times of israel som kilde hvis der
  ikke er andre': it leads a story only when no other outlet can, and an event page credits it only for a number no
  other outlet carries) and `wire` a one-line statement feed (Al Jazeera urgent: counts as an outlet, feeds
  `lines.json` and the Bevægelser briefing, never a card of its own). `"scout": true` (18/10) marks a Google News
  search on a subject across outlets (states' borrowing stress, central banks, deadlines, Danish deadlines): its items
  keep the outlet Google names, and an outlet that is no source of ours is off the scale (`run.OffScale`). A scout's new item is looked up before it enters (`radar/fresh.py`: Google's link resolved, the address's month and the page's own date read); one older than `scout_max_age_days` (2) is left out – Google dates an old page anew when its outlet touches it. `"scale": false` marks a source added for its
  camp (31 of them, 2026-10-17): it never moves the established sources' scale (taste percentiles, a section's bar,
  the outlet lift, big stories) and leads at most `max_added_per_day` (config/settings.json, 3) cards of its own a day,
  and only stories no established source carries. The movement's own outlets (group `bevægelsen`) never count as an
  outlet or confirmation, and governments' channels (`official`) never lead a story others carry. `fit` (0.5–1.3,
  measured 2026-10-17, docs/hjerne/kilder-maaling.md) says how well a source serves the editor: among the outlets that
  may lead, the lead is the best of fit + 0.35 for a Danish headline + 0.1 with a teaser − 0.5 for a curiosity headline
  (`lead_danish`, `lead_curious`), and the rank gets `rank_fit` × (fit − 1) (−5 … +3). Per source `drop` / `cut`
  (regular expressions) clean headlines at intake and once over the kept items (`feeds.tidy`: Times of Israel's blogs,
  Jerusalem Post's opinion pieces, BT's betting ads, Ahram's sport and section tails, Shafaq's prefix); for every
  Google News source the site-name tails go, for every Telegram channel a speaker-only first line is joined to what was
  said, and a post's language is sniffed (`feeds.sniff`: Turkish posts in an English channel).
- `src/radar/headlines.py` – `curious(title)`: the radar's test for a curiosity headline (a question, 'Derfor/Se/Her
  er/Sådan/Hvorfor …', 'Why/How/What …', tabloid labels, '- opinion' at the end, a line that only names who speaks).
  The app holds a copy (`curious` in app.js) – keep the two alike; the editor's stricter one is `voice.curiosity`.
  Also (2026-10-17, pro-plan): `clean_teaser(text, title)` – a teaser without its call to action ('Følg udviklingen …
  her', 'Læs mere'), links and a picture's caption with its credit and markup (`feeds.tidy` at intake and over the kept
  items; the app's `cleanTeaser` is the copy), and `commentary(link, title)` – an opinion or analysis piece by its
  section's path or its label; `run.py` writes `kind: 'kommentar'` into data.json and app.json when every readable
  article of the story is one (`story_kind`; a news report leads before a column: `lead_comment` 0.6 in the lead's
  quality) – the app's `isComment` reads older copies the same way –, the editor's input lists it, a commentary is never
  a 'top' block and never notified. A big story's notification says 'Topnyhed' only when the app shows it so (`top_now`
  = the app's `topNow`: the day's five), else 'Vigtig nyhed'; a new answer's says its title in Danish (machine-translated,
  else 'Et nyt svar på politiske spørgsmål'). The
  notification says the app's headline: `run.push_headline` takes the editor's (summaries.json, `RADAR_SUMMARIES` from
  the digest branch), else the Danish, the translation, the outlet's; a curiosity headline gives way to the teaser.
  search.json carries `da` (the Danish headline).
- `src/radar/level.py` – **Live's level** (the owner's rule of 2026-10-17, notes-owner-volume.md): the editor's
  `få` / `normal` / `mange` in `live.json` (digest branch, read by radar.yml into `.cache/live.json`, `RADAR_LIVE`)
  becomes a rank floor and a soft count for the last 24 hours (settings `live_levels` {få: [104, 20], normal: [96, 38],
  mange: [88, 72]}); a story once admitted stays while its rank is within `live_keep_margin` (4) of the line; big
  stories and confirmed Danish stories on Islam, Muslims, integration and foreign policy (tier 6 or a `protect_dk` word
  in config/sections.json) are never cut; take admits a story, drop removes one (even a big one); for one story the
  newest day's decision wins, on one day drop wins (`decision`). The level holds for the Danish day while live.json is
  younger than `STALE` (6 h) between 06 and 24, and between 00 and 06 the evening's level holds until the morning's
  update; otherwise `normal`. Admissions are remembered by member in `state/admitted.json`. data.json keeps the whole
  candidate pool (each story's `live` = why it is in, or null; a top-level `live` block with level, why, line, counts,
  take, drop); **`app.json`** holds what the app shows – the admitted stories of 48 hours and the big ones not dropped
  (`in_app`) – with only the fields app.js reads and empty values left out (shape: docs/hjerne/notes-r2-radar.md §4).
  Notifications go only to stories Live shows. Tune with `RANK_CHECK_LEVEL=få|normal|mange py scripts/rank_check.py`.
- `src/radar/method.py` + `config/method.json` – **the brain in the selection** (2026-10-17): every story gets the
  heaviest of the books' 13 tiers its headline shows, the powers as Hizb ut-Tahrir's newest answers read them (each
  reading dated and attributed in `_why`: USA leading; Britain and France weakened great powers; Russia a middle power
  since 12/6/2026 and China a regional power – their own acts are the major issues, tier 5, their dealings with the USA
  tier 1; Germany and the EU actors). Lifts 1:+10, 2:+8, 3:+6, 4:+6, 6:+6, 7:+3, 8:+3, 9:+1, 11:−4, 13:−8 (5, 10, 12:
  0), positive ones only when an established outlet carries the story; tiers 1–4 and 6 with rank ≥ 45 reach the editor
  below the taste bar (≤ 20 a day, `method: true`). Each story also carries `members`, `camps`, `first`, `actors` (wiki
  ids), `tier`, `tags`, `powers`. The app shows none of it as analysis. Tune with `scripts/rank_check.py`
  (`RANK_CHECK_OUT` keeps the pass's files for an app preview, `RANK_CHECK_STATE` replays a saved snapshot).
- `src/radar/analyses.py` reads the amir's list of political answers every 3 hours (`RADAR_ANALYSES: '1'` in
  radar.yml) and keeps, in `state/analyses.json`, the text only of answers the static layer (`public/viden`) lacks; the
  editor files them in `answers.json`. The repository is public: no answer texts in committed files.
- `public/viden/` – the movement layer and the wiki, built locally and committed: `scripts/build_movement.py` →
  `movement.json` and `movement-index.json` (the 321 political answers 2004–2026 as dated Danish readings in plain
  Danish – every text under its dated answer, none naming the movement; the build works on the attributed form and
  writes each text's plain form from `docs/hjerne/uden-ifolge.json` as its last step, which `build_begreber.py` reads
  back);
  `scripts/build_begreber.py` → `begreber.json` and `begreber-index.json` (203 pages: states, powers, groups, issues and
  the concept pages of `docs/hjerne/begreber-ideer.json`; aliases are Danish news forms, never an adjective, a people's
  word or a capital for its government). A test fails when the committed wiki is not a fresh build.
- `src/radar/thumbs.py` gives every card a small picture (feed image → another outlet's → the og:image of the lead's
  article page, then of up to four other outlets' pages; a story without one shows its outlet's initials in the app –
  the owner likes those tiles and declined pictures found by the editor, 2026-10-11; the chosen original stays in `pic`,
  which app.json carries and Dagens historie shows large since 2026-10-17),
  shrunk with Pillow to a 144 px JPEG in `state/t/` (served from the data branch); unverified Telegram channels
  never lend one. `state/pics.json` remembers page images and failed pictures for 3 days.
- `src/radar/reader.py` (18/10, the owner: 'Se kilderne her, hvorfor kan vi ikke bruge de samme?'): in the cloud run
  (`RADAR_READ=1`) the article pages of the ten most widely carried stories in Live are read (Google News links resolved
  by `fresh.resolve`) and up to six sentences with a count kept per article with its outlet (`said` on the card in
  data.json, `state/read.json` remembers pages two days) – the editor's material for event pages (events.story_text,
  carriers, material); only single sentences, never an article, and the app shows none of it.
- `src/radar/places.py` (18/10, the owner: 'Lad os lave kortet'): the event pages' places (events.json from the digest
  branch, `.cache/events.json`, `RADAR_EVENTS`) looked up once each in Nominatim (≤ 12 a run, a second apart, a
  User-Agent naming Khabar) into `places.json` on the data branch ("<place>|<kicker>" → [lat, lon, country|state|city]);
  the app's event page draws a map from it, framed by the places' own spread – at least `MAP_MIN_KM` (40) each way – or
  by the editor's `map` {km, focus} (19/10, the owner: 'den er alt for zoomet ud'; `evFrame` = `events.frame`, and every
  input says under each page what its map shows: `map_line`) (`evMapBox`, `evMaps`: OpenFreeMap's vector map through the shelved Kort
  section's `loadVector`/`kStyle`, without its own names; `data-keep` lets `morph` leave the map's elements alone).
- **The large pictures** (18/10): `thumbs.large` grades every outlet's picture of the 18 strongest stories in Live and the
  big ones (`fitness`: wide, sharp, light, a scene or a small high face; the face's height is `pf[4]`), keeps the best as
  the card's `pic` with its `pf` and a light copy `pl` (960 px, state/l/, kept per picture in pics.json `grade`); the app
  loads `LIGHT + pl` (`picSrc`), the original when the copy is gone (`picFallback`), and sets the face in the free band
  above the measured headline, or – where it does not fit there – as high as the frame lets it: the headline always lies on
  the picture (18/10, the owner: 'teksten skal altid være i det format at det ligger på billedet'; `placePic`, `picPlace`).
- `src/radar/push.py` sends Web Push; `src/radar/feedback.py` reads copy taps from the ntfy.sh relay. A notification
  (18/10, `run.push_note`): one story – its weight, its headline, one line of résumé (`push_line`) and `?item=`; several
  – their headlines as a list and `?nye=<ids>`, the 'Nye historier' page. The service worker shows nothing while the app
  is in view (it tells the page to fetch; Safari gets a silent one closed at once) and a tap opens the link in the open
  app by a message (`routeLink`); the page has no 'nye historier' pill.
- `src/radar/stats.py` keeps the owner's statistics (2026-10-11): the app posts `visit` (home screen or browser, iPhone/Android/other, time zone, language, how it came; `first` on 'Kom i gang') and `leave` (seconds, tabs, stories opened) to the relay; read/share signals give the most read stories (the owner's own carry `me` and are not counted). Counts per Danish day in `state/stats.enc`, AES-GCM with a key from ADMIN_KEY (sha256('khabar-stats|' + code)); the app decrypts it in the admin-only block at the top of Indstillinger. Nothing is stored on phones and no id follows a person – the owner declined anonymous ids for unique visitors (2026-10-11: consent rules) and wants no consent prompt or button, so place in Denmark is not collected (it would need a permission prompt or an IP lookup); country comes from the time zone.
- `scripts/editor.py` is the Claude editor's tool (gate / check / input / publish, see its docstring). `check` is the
  quarter-hour look (≤ ~40 lines: the radar's last pass, the stories of weight – a story is new only when its first
  article is, a pick or recap story is marked and calls for nothing –, verdict INTET NYT AF VÆGT or OPDATÉR: why);
  `gate` is the same look in Actions that fires the routine (one fire per reason, none while an update is under way,
  `editor_fires_per_day` a day spread over the day, at night only for a big story); `input` carries the brain
  (`scripts/brain.py`: the order of weight and each power's current reading, ≤ 6,000 characters) and the front page
  now (a reading the editor filed in `answers.json` governs the brain's line for its subject when it is newer than the
  wiki's); `publish` keeps what a small update leaves out (lede, picks, quotes), checks all of the editor's own text –
  lede, summaries, recap lines, topic names, picks' why – with `scripts/voice.py` (the content rules; reality only,
  never the movement's reading as fact; a line or quote from the movement's or a government's channel gets the
  movement's checks too) and files a new answer in `answers.json`. **The calendar (17/10):** an update's optional `calendar`
  list (date YYYY-MM-DD, or YYYY-MM with `approx`; title, kind, place, why, link, ids) is checked like headlines
  (`voice.check_headline`, `check_reality`, and `voice.check_forecast` – no forecast in the title or why) and kept in
  `kalender.json` on the digest branch (in `DIGEST_FILES`; an entry stays until two days after its day, the same id
  changes it, `{"id": …, "remove": true}` removes it); the input lists the calendar's next 30 days (calendar.json
  and kalender.json) so the editor adds only what the news name and the calendar lacks. **Round 2 (2026-10-17):** the input lists up to
  `MAX_TITLES` (30) stories in Live still without the editor's headline ('Headlines to write': big first, then those the
  app shows worst, with the outlet's headline, teaser and three other outlets'), Live today (level, note, count, the
  radar's line, the six weakest in and strongest out, yesterday's take/drop still in force) and the front page's
  composition with its palette; `publish` checks every headline, block title and front-page line with
  `voice.check_headline` (no curiosity headline, no '– video', no judgement of its own unless 'Who: what'; since the
  pro-plan also `voice.check_prefix` – 'X:' with a news outlet's name only when that outlet carries the story; a
  government's channel ('Kreml', 'Det Hvide Hus') or the movement's is a speaker, never refused (`voice.NEWS_GROUPS`) – and
  `voice.check_lede` – a new lede whose first clause shares 60 % of its words with Dagens historie's headline is
  refused: a standfirst names the day's other stories; the check notes a main story's timeline that shares fewer than
  three words with it, `timeline_off`), files
  headlines under the story's id with its members (summaries.json `titles`; one that breaks today's rules covers no
  story and is removed at the next publish), writes `live.json` at every publish (today's and yesterday's Danish days;
  take/drop add to today's) and `front.json` (the composition: at most 6 blocks (`FRONT_BLOCKS`; the app draws no more) of top, liste, udvikling, citat, svar,
  live, linje; the lede's optional `lede_ids`, one story id per part of `lede_parts`, checked like the picks, kept with a
  kept lede, beside the lede in digest.json's notes and front.json; a story once; its stories in Live or taken in; a kept composition is re-dated, minus stories that left
  and – after midnight – its linje blocks). The check's Live line and two more reasons: 8 stories waiting for a
  headline (once per update) or one waiting over 45 minutes between 06 and 24 (once per story), and today's få/mange
  about to lapse (live.json 5 h 15 min old). It keeps one overview per
  Danish date: each update adds short 'Who: what' lines to the day's topics (newest first); the day lists every
  wire line id its updates were given (`ids`), so the next update gets only new ones. Old edition archives
  (`briefs`) are folded into days automatically.
- `scripts/events.py` – **Begivenheder** (2026-10-18, the owner: 'undersider hvor vi følger med i begivenheder med
  faktabokse'; 'objektive til selve begivenheden, ligesom vi får beskrevet i vores thaqafah … fakta, begivenhed og
  tal'): the editor's `events` in an update become `events.json` on the digest branch (in `DIGEST_FILES`; at most
  `MAX_EVENTS` 5, a page kept `EVENT_KEEP` 4 days after its last change, merged by id, `remove` removes one). **A fact box
  holds a number of news value only – the event's size as a whole – and a page may have none** (19/10, the owner:
  'enten findes bedre faktatal ellers ingen skal vises. dette skal være en generel regel'; `FACT_RULE`): the tool never
  asks for boxes because the stories carry numbers (that demand made weak boxes). Every number in a fact's
  value, its `of` and `was`, and in an article paragraph must stand in the stories it cites (`grounded`, digits
  normalised; dates, years and clock times exempt in paragraphs), an article paragraph with an opinion, judgement or
  forecast is refused (`OPINION`), and every text goes through voice.py. The page's picture and its face (`pf`) come
  from its first story with one. The app: the side page 'begivenhed' (`eventPage`, `?begivenhed=<id>`) and the front
  page's modules `begivenhed` (`eventCard`), `tal` (`numberBlock`) and `nedtaelling` (`countdownBlock`); an event under
  way that the editor did not place gets its card after the first block, one ahead within a week its countdown
  (`eventsUnplaced`). The fact boxes (`factBoxes`, `factCell`, `factGraphic`, `factDelta`): hairlines, no boxes, the
  first number large; a share of ten as dots, another share a meter, a number with `was` two bars and the change; each
  box names who gives its number and the outlet that carried it ('… · via Al Jazeera', `factWho`, 19/10).
- **The front-page archive** (18/10, the owner: 'ja lav et arkiv, men kun ved dagens sidste opdatering. så vi får et om
  dagen'; open to every reader but quiet – my recommendation, not a tab): `editor.py publish` with a composition writes
  the Danish day's front page (`front_snapshot`: the blocks with the stories as shown – `arch_story`: the editor's
  headline, else the Danish, else the outlet's, a curiosity headline giving way to its teaser –, the events placed or
  set in by the app with `geo`, the quote, the Live block's stories, the day's recap) to `arkiv/<date>.json` on the
  digest branch over the day's earlier one, `arkiv/index.json` (`archive_index`) one row a day kept for good, and the
  main stories' and events' light copies as `arkiv/img/<date>-<id>.jpg` (`push(…, pics)`: the data branch's blob put
  in the digest tree by `tree_of`; a picture of the day its page no longer shows goes). The app: the side pages
  `forsider` (`arkListPage`) and `forside` (`arkPage`, `?forside=<date>`) – the front page's pieces in its look
  (`.page.fp` on both pages; the CSS's front-page rules use the class), archived rows under their own ids (`arkItem`,
  `a<yyyymmdd>-<id>`, `sid` the story's), events frozen at their day (`e._day`, `arkEvent`); the ways in are `arkRow` at
  the front page's foot and `arkLinkFor` under an earlier day on Udvikling. Today is the front page itself: the list
  holds the days before it.
- **Dagens historie as an event's card** (20/10, the owner: 'Dagens historie er en gentagelse af en begivenhed'): when the
  day's first main story belongs to an event under way (`eventOfStory`), `eventCard(ev, 'Dagens historie')` leads in its
  place (composedHome and fixedHome), and the event is kept from being set in again (`frontBlocks(…, leadEv.id)`).
- **The front page's rhythm** (19/10, the owner: 'fast afveksling'): `frontRhythm` (no two of one look together while
  another can go between) over `frontOrder` (the order of weight) over `frontBlocks` (the unplaced event's card and, when
  the composition has none, a quote, else a development, else a number, `auto` – extra to FRONT_MAX). **A headline its
  story outgrew** (`editor.stale_heads`, `stale_lines`): the input lists it and the check calls for an update.
- **The runs** (19/10, the owner: 'en widget på indstillinger for admin så jeg kan se hvad tid forskellige redaktører og
  andre automationer kører'): the admin block's 'Kørsler' (`RUNS`, `runsHtml` in app.js) shows every editor and automation
  with its clock in Danish time (from the UTC hours; summer/winter handled), its last and next run and an editor's last
  update from runs.json (digest branch; `editor.runner` names the editor – its memo or answers, the report, the economy
  day, else the hour's – and `run_note` what it did; 120 kept). **When a routine's cron changes, change `SCHEDULE` in
  editor.py and `RUNS` in app.js too** (tests/test_editor.py keeps them alike).
- **The owner's comments, his headlines and the admin sheet** (18/10, the owner: 'Giv mig også et felt hvor jeg kan
  skrive en kommentar til elementet til redaktørerne … alle elementer burde kunne holdes nede … giv også en funktion der
  lader mig edit overskrifter direkte … ryd op i admin funktionerne'): in admin a long press on any element of any page
  (`holdable`, `heldInfo` – a reference `ref` like 'story:<id>', 'ev:<id>:fakta:2', 'kal:<id>', 'forside:overblik',
  'side:<page>:<block>', where it sits and its words `seen`; Økonomi's frame sends its own through `khabarOwnerHold`)
  opens the owner's sheet (`openAct` for a story, `openHeld` for the rest, `openQuotes`): Kommentar · Ret overskrift ·
  Kopiér tekst, the picture, Prioritet and Sektion as `.seg` segments, Dagens historie, removal last. A comment
  (`noteView`, `sendNote`) is the signed action `note` (id = ref, why = the words, sec = where and what it showed, at = its
  id 'n<ms>'); admin.py keeps it in removed.json `notes` (14 days, `unnote` removes); editor.py's inputs list the open ones
  by scope (`note_scope`: oko → the economy editor, kal → either, svar/begreb → the builder, the rest the front-page and
  senior editors; `noteScope` in app.js is the copy), the check's verdict holds while one waits, an update answers in
  `owner_notes` → owner.json (digest branch, 14 days), shown under 'Dine kommentarer' (`commentsHtml`). His headline
  (`titleView`, `saveTitle`; act `title`, removed.json `titles` – a story's 4 days, an event page's 'ev:<id>' 30) is
  data.json/app.json `owner.titles`: `display` takes `ownerTitleOf` before the editor's, over a 'top' block's own title,
  `events()` over an event's; run.py puts it over the editor's in the notifications, editor.py's `headlines_of` counts it
  as written (`owner: True`, never refused) and the archive keeps it; the inputs list his pairs (`owner_title_lines`).
- **The owner's picture choice** (18/10, the owner: 'vælge mellem 3 billeder når jeg holder nede på de store artikler
  … redaktøren vil også … lære af dette og forstå min smag for billedvalg'): `thumbs.large` keeps the best `CHOICES`
  (3) pictures of each strong story with their light copies as the card's `pics` [{k (pic_key), u, pf, pl}] (app.json
  carries it); the owner's long press on a large story (`openAct`) shows them, a tap sends the signed action `pic`
  (admin.py; `state/removed.json` `pics`, kept three days, `data.owner.pics`) and shows it at once (`ownerPicOf` in
  `display`); the radar's large() then takes his choice (`chosen_by`) and learns from it once (`learn`, `taste` in
  pics.json: feature and outlet weights, `taste_bonus` ≤ ±2 on fitness). An event page's picture the same way (19/10):
  its stories' best pictures (`evPicChoices`), the choice as 'ev:<id>' among his pictures, learned once in `large`
  (`events`), kept on the page by `editor.event_pictures` → `events_file(chosen=…)`.
- **Faces in large pictures** (18/10): `thumbs.subject` keeps where a picture's face sits (`spot` in pics.json, card
  `pf`, app.json carries it); the app's `placePic` sets the picture so the face sits about a quarter from the top, and
  where it would sit under the text, it goes as high as it can and the headline stays on the picture (`tx-below` is no
  longer set, 18/10). Dagens historie's picture carries its headline only – no outlet, time or count of outlets (the owner,
  18/10: 'for at få mere plads til tekst der ikke dækker billedet'); the opened story names them. A picture is never
  dragged (`-webkit-user-drag: none`) and an event's picture leaves the finger to its frame, so the owner can hold it. An
  event page's map takes a new look in place when the setting or the phone's own changes (`evMapsLook`).
- `src/radar/osint.py` (**shelved since 17/10** at the owner's wish: "Du skal kassere kortvisningen, eller gemme den, i
  hvert fald for nu, og ikke lave videre på den … den bidrager ikke til det store billede"): it wrote `map.json` for the
  Kort tab from data.json and the editor's headlines, placing violent events at the places of `config/map-places.json`.
  The code, the places and tests/test_osint.py stay; radar.yml's Map step is `if: false`, the app has no Kort tab and
  its Kort section in app.js is never called (tests/test_app_kort.py checks that it is shelved and loads nothing). The
  15 sources added for the map stay in feeds.json (they feed Live). To bring it back: the tab, its page, SWIPE_TABS,
  the callers and listeners noted in the section, the step, and `mapUrl`/`cartoKey` in pages.yml.
- `src/radar/calendar.py` (2026-10-17, the owner: "en kalender, som viser fremtidige begivenheder … ting, der har
  geopolitisk betydning … hvad der skal til at ske snart, af planlagte begivenheder"; the Islamic dates left out at his
  wish the same day) writes `calendar.json` for the Kalender tab after the energy step (stdlib, continue-on-error, 3
  minutes). Sources, each on its own daily clock, a failed one resting three hours and keeping its last good items:
  Wikipedia's "<year> national electoral calendar" for this year and the next two through the MediaWiki API
  (action=parse, a descriptive User-Agent with no personal data; a page that does not exist yet is an empty answer),
  kept to the countries of weight (`COUNTRIES`: every Muslim-majority state, the great powers, the EU states, Israel
  as “israel”, Ukraine, Brazil), local elections left out, a month only or "by" marked `approx` ('forventet'); the
  Fed's FOMC calendar and the ECB's meeting calendar as decision days (Danmarks Nationalbank follows the ECB); and
  `config/calendar.json`, the curated summits and fixed dates, every one with its checked source (dates that could not
  be checked are left out and named in its `_help`). A curated election wins over Wikipedia's on the same day and
  place; past events are kept 30 days (the tab's 'Tidligere'). Item shape: id, date (YYYY-MM-DD, YYYY-MM or – since
  18/10 – YYYY: the year alone, 'i løbet af 2027', for Wikipedia's 'Unknown date' elections and the annual meetings
  whose date is not announced; India's Council of States and an undated election the page also dates are left out),
  end, approx, title, kind (valg | topmøde | centralbank | frist | retssag | forhandling | dansk | andet), place, why,
  link, src, w (a curated event may set its weight). Wikipedia has no 2028 page yet: 2028's elections of weight
  (Tyrkiet, Iran, Malaysia, USA) are curated. Every central bank's rate decision is of low weight (the owner, 18/10:
  'abstrakt'). Reality only: what happens, where, one factual line on why it matters – never a forecast. **Dates in the
  news (18/10):** `editor.py input` lists, under 'Dates in the news', the stories of the last two days that name a
  coming day (`date_in`) with an event's word, or a deadline's own word without one (`DEADLINE`, `EVENTISH`), each with
  what the calendar holds on that day; the editor decides on every line (the routine prompt says so).
- `src/radar/energy.py` (2026-10-17, owner's request: an OSINT page for oil, fuel and the real market; the energy chat was merged into this project's main chat the same day;
  the same day made **the economy page**, the owner: "en femte fane med olie, diesel og benzinpriser … generelle
  geopolitiske tal man skal holde øje med og hvorfor … s&p 500 … landes gæld … AI boblen … interaktiv … live") writes
  `energy.json` for `public/energi/` (khabar.nu/energi; in the app's fifth tab Økonomi as `energi/?embed=1`, a frame
  the other part of the app owns) after every radar pass, stdlib only, a step in radar.yml that may fail without
  stopping the save. Sources, all keyless: Yahoo Finance's chart API (oil, product and gas futures, contract months
  for the curves, USD/DKK and EUR/DKK, the indices ^GSPC ^NDX ^STOXX50E ^OMXC25 ^N225 000001.SS, the VIX, ^TNX, the
  dollar index, gold, copper, wheat, Bitcoin and the AI giants NVDA MSFT GOOGL META AMZN AAPL TSM AVGO – each with its
  session `o` [start, end], so the page tells a live price from a close), EIA's own daily history pages for the
  physical prices (gas: the static `rngwhhdD.htm`, its LeafHandler is a 404; FRED's CSV as the fallback – it does not
  answer GitHub's runners), EIA's weekly retail gasoline and diesel, US average (`eia_weeks`, two years of Mondays),
  the EU's Weekly Oil Bulletin 'latest prices with taxes' (a stable document id; the .xlsx read with zipfile,
  `xlsx_rows`; EUR per 1000 l, its EU average kept weekly for two years), State Street's daily SPY holdings .xlsx
  (the AI giants' real weight in the S&P 500 – Alphabet's two classes added, TSMC not in the index – the ten largest,
  the basket's share kept by day), the Treasury's Debt to the Penny (600 rows; `g` = growth a day against the figure
  nearest a year earlier) and the IMF DataMapper's GGXWDG_NGDP for 16 lands up to last year (the current year is a
  projection; the IMF turns a browser-like agent away and lets Python's own in), Circle K's public price API (header
  X-App-Name: PRICES; Circle K + INGO) and q8.dk/Station/GetStationPrices (Q8 + F24). Each source has its own clock
  (EVERY: markets 4 min … IMF a day) and keeps its last good numbers, one that failed rests RETRY (30 min), and the
  five slow ones are asked side by side (a cold run ~35 s, a warm one < 1 s); pump prices keep one point a day for 400
  days; a chain's 'ændret' is the change time of its stations at the list price; the news are data.json's oil and
  fuel stories with the editor's headline (RADAR_SUMMARIES), no wire lines. energy.json is ~150 KB (markets 6 months
  daily). **The page** (Økonomi; since 17/10 evening, the owner: 'uoverskuelig … scroll ned og den skifter i mellem
  forskellige emner med tydeligt emneskift'): **one long page** of seven topics in a fixed order (`TOPICS`) – Lige nu,
  Brændstof, Olie og gas, Markeder, AI, Gæld, Råvarer – no tab views, no chips. Each topic (`<section class="ec-sec">`)
  opens with generous space, a short red rule, the red fly title and one headline line (h2) in Source Serif 4 made from
  the numbers, reality only (`head`, `phrase`: 'Brent steg 3,7 % fredag', 'Benzin 17,69 kr. – diesel 18,89 kr.',
  'USA’s gæld: 40,4 billioner $'); then 3–4 key figures as large tiles (name, value, the move with an arrow, a
  sparkline – `tilesOf`; a tap opens one at a time per topic, its chart and texts under its row), then one quiet
  'Flere tal' row that unfolds the rest in place, made only when unfolded (Brændstof: the chains with premium and HVO,
  the raw product's share and rows, US diesel, the EU table; Olie: physical market, curve, crack spreads, products, gas,
  news; Markeder: the other indices, dollar and currencies; AI: the six other companies and why people speak of a
  bubble – no prediction; Gæld: the IMF lands beyond the top five and IMF's texts), then one line with the topic's time
  and sources ('Opdateret kl. 18.46 · fredagens lukkekurser · kilder: …', `meta`/`baseOf`): a figure says its own time
  ('torsdag lukkekurs', 'kl. 18.46', 'ugentlig · 12/10', 'dagligt · 14/10', 'årlig · 2025') only when it differs from the
  topic's. Gæld: the counter that ticks the last year's average growth onto the last official figure, labelled 'Skøn'
  and said so, then the IMF's five highest bars. Lige nu: only the four biggest moves against each figure's typical day
  (at most two from one topic), each a tap to its figure in its topic (opened, unfolded if need be: `goFigure`). The
  dock at the bottom (the frame's bottom when embedded; a nav of links with `aria-current`) follows the scroll: an
  IntersectionObserver with a line just under the bar (`watch`; the foot in view means the last topic), never a scroll
  listener; a tap jumps (smooth unless Reduce Motion, the dock held on its goal meanwhile, `jump`), the chosen chip
  scrolls into view inside the dock when it overflows, and `#nu` … `#raavarer` follow by `history.replaceState`, never a
  history step (a link with one opens there). Every figure opens a chart with ranges its history fills and three
  texts – Hvad er det, Hvorfor holde øje med det nu, Stiger det / Falder det – factual and neutral; nothing is opened
  from an earlier visit (only the chosen ranges are remembered), so no chart is drawn before a tap. The foot says
  'Siden er information, ikke investeringsrådgivning.' Reload every 5 minutes and when the page is shown again; a file
  the same as last time draws nothing, a new one redraws every topic with the topic in view kept in place. Israel's name in the bars as “israel”. The page holds all names, units
  and explanations; the file only numbers (tests/test_energy.py checks both).
- `public/` is the PWA. `config.js`, `data.json` and `dev/` there are local-preview only (gitignored);
  `pages.yml` generates the real `config.js` (data, app, digest, front, search, moves, answers, analyses, energy
  and the calendar's two URLs: `calendarUrl` on the data branch, `kalenderUrl` on the digest branch). A local preview of round 2's data: `public/dev/r2/` with `?dev=r2` (`&front=0` the fixed front page, `&app=0`
  data.json instead of app.json) in the local config.js.
- State lives on the force-pushed orphan branch `data` (no history), read back at the start of each run.
- `config/profile.enc` = output of `scripts/build_profile.py` (shared links + statement lines from link-less briefings;
  no member names), AES-256-CBC/PBKDF2 (200k iterations) with `PROFILE_KEY`:
  `openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in .cache/profile.jsonl -out config/profile.enc -pass env:PROFILE_KEY`

<!-- How the pieces fit together. Where the entry point is. What depends on what.
     Update this when the shape of the project changes. -->

## Scheduling and Claude routines

- GitHub's own `*/5` schedule is unreliable (it ran once in a whole night). The real clock is an external
  scheduler (Upstash QStash or cron-job.org, set up by the owner) calling the workflow_dispatch API with a
  fine-grained token limited to Actions on this repo. GitHub's schedule stays as a fallback.
- **The clock (since 2026-10-11):** Upstash QStash schedule `nabd-radar` (owner's account, eu-central-1) calls the
  workflow_dispatch API every 5 minutes with a fine-grained GitHub token (Actions read/write on this repo only, made
  by the owner; it expires – renew it and rerun `scripts/setup-clock.ps1`). The PC task 'Nabd vaekkeur' is removed.
- Claude Code cloud routines on the owner's subscription (claude.ai/code/routines):
  - **The quarter-hour look (hjerne branch, the owner 2026-10-17: "Claude skal køre hvert 15. minut på siden og vurdere,
    om der er noget, der skal tilrettes. Der er tokens nok"):** routines have a daily run cap per account (about 15 on
    Max by third-party reports; read the real one at claude.ai/code/routines), so 96 runs a day cannot work. The look is
    `editor.py gate` in radar.yml after every radar pass (no tokens); when its verdict holds it fires the editor's
    routine through its **API trigger** (GitHub secrets `ROUTINE_FIRE_URL`, `ROUTINE_FIRE_TOKEN`; without them a dry
    run), at most `editor_fires_per_day` (config/settings.json, 12) a Danish day, two kept for the morning and the
    evening; every fire is kept in `state/editor-gate.json`. The routine has the prompt `docs/hjerne/routine-prompt.md`
    (the private weighing guide inserted at `[WEIGHING-GUIDE]`) and no schedule; it starts with `editor.py check`, may
    stop with one line, else `input`, a small update and `publish --push` (which refuses when another update landed
    meanwhile). About the tokens of today's twelve updates (docs/hjerne/cadence.md). At launch the owner adds the API
    trigger to the editor routine below, removes its schedule and gives it the new prompt.
  - `trig_01B5p6DmEx8pz9cDLZzwxbHj` editor (until the launch): fires twelve times a day (since 2026-10-11, the owner's choice, ~1/10 of his plan):
    06, 09, 12 and 14-22 UTC = 07, 10, 13 and every hour 15-23 Danish winter time (an hour later in summer); each update
    is small – only what is new since the last; the app says the recap is 'opdateret løbende fra morgen til aften'. It has NO internet (the cloud sandbox blocks it; the owner
    chose not to open it): everything comes from `editor.py input`, kept lean for tokens (40 top stories, yesterday's
    recap only as topic names after 10, stories listed once, 6 summaries per update with readers' opened stories first from
    learned.json; since round 2 up to 30 headlines to write, Live's level and the front page's composition – about
    53,000 characters, docs/hjerne/cadence.md). It runs
    `scripts/editor.py input`, then writes one update: picks (stories that matter most geopolitically; for Danmark,
    those useful in the group's dawah), moves (stories in the wrong section), quotes (best statements, in Danish) and
    summaries (2–3 Danish sentences for up to 6 stories from headline, teaser and other outlets – always `paywall:
    true`, and the app says the summary rests on the headlines and introductions), titles (since round 2 an informative
    Danish headline for every story in Live without one, Danish outlets too, which the app shows instead of the
    outlet's), the day's level with take/drop/note (`live.json`), the front page's blocks (`front.json`), recap lines (at most 5 'Who: what' lines, filed under the Danish
    date they happened; a topic continued across days is a development on the app's Udvikling page), and runs
    `scripts/editor.py publish --push` → `digest.json` (the day shown + `editor` notes the app applies), `moves.json`
    (30 days), `summaries.json` (summaries in `items`, checked headlines in `titles`; 4 days), `live.json` (the level;
    two Danish days), `front.json` (the composition) and `answers.json` (the
    amir's answers filed after the static layer, with Danish readings and begreber ids; kept forever) on the orphan
    `digest` branch. The launch steps (merge, secrets, the routine's trigger and prompt): docs/hjerne/launch.md. Only the first update at or after 21 Danish time notifies the phones.
    The routine prompt also holds the owner's WEIGHING guide (what matters most geopolitically, from his own reading; it orders the lede, picks and topics, never the wording). It lives only in the private routine prompt: keep it out of this public repo.
  - `trig_019VrGU5HBU66UxcDjqEavok` **the event editor** (Khabar · begivenhedsredaktør, 18/10, the owner: 'Sæt begivenheds
    ekspert redaktøren op …' – four times a day – 'Ekspert redaktøren må også gerne kigge på forsiden … give besked til
    khabar hjernes næste kørsel'): claude-opus-5-5, cron `0 7,11,15,19 * * *` = 08, 12, 16, 20 Danish winter time (an
    hour later in summer). It builds and keeps the event pages whole and looks over the whole front page, improving it in
    the same update, and leaves the front-page editor a `memo` (memo.json on the digest branch; the input shows the notes
    of the last twelve hours first; a new one from it calls for the front-page editor's update). Its public prompt:
    docs/hjerne/routine-event-prompt.md (the weighing guide kept private). Both editors work from the thaqafah and the
    brain's understanding of the world, and Khabar's understanding is an ordinary da'wah carrier's (no quotation marks
    of distance, `voice.check_distance`).
  - `trig_0173anatkjQydMipc98PpqZG` **the chief editor** (Khabar · chefredaktør, 18/10, the owner: 'ja sæt den op kl 5'):
    claude-opus-5-5, cron `0 4 * * *` = 05 Danish winter time. It reads the last day's own text (`editor.py input
    --audit`), corrects what falls short, keeps the fejlbog (`lessons.json` on the digest branch, `lessons` in an update,
    ≤ 40 rules; every input shows it first), leaves the 07 senior editor a memo and writes the owner a morning report
    (`report`, report.json, shown first in the owner's admin block). Public prompt: docs/hjerne/routine-chief-prompt.md.
    The senior editor (`trig_019VrGU5HBU66UxcDjqEavok`, cron `0 6,11,19` since 18/10 evening) takes 07, 12 and 20 in
    place of the front-page editor (`trig_01B5p6DmEx8pz9cDLZzwxbHj`, cron `0 5,7-10,12-14,16-18,20-22`).
  - **The economy editor** (Khabar · økonomiredaktør, 18/10, the owner: 'kan vi erstatte en af senior kørslerne i løbet
    af dagen som kan kigge på økonomi og kalender siden? tilføje kontekst forbedre layout og gøre det mere livligt. en gang
    om dagen er nok … primært til økonomi siden'): claude-opus-5-5, cron `0 15 * * *` = 16 Danish winter time, the senior
    editor's former 16 o'clock run (the front page has no update that hour: the front-page editor runs at 15 and 17). It
    reads `editor.py input --okonomi` (the page's figures, the economic news of 36 hours – energy.NEWS, energy.CRISIS and
    okonomi.MARKETS –, the fortnight's planned events with their ids, its own last day) and writes `okonomi` – `dag`, a
    line and up to three stories per topic (`emner`), up to four `kommende` dates, the day's `citat` – plus headlines,
    summaries and calendar entries; `scripts/okonomi.py` checks it (every number from a cited story, no judgement,
    forecast or advice on money – `ADVICE`) into okonomi.json; the radar's energy step reads it (`RADAR_OKONOMI`,
    `energy.editor_layer`, dropped after 30 hours) into energy.json's `ed`, and the page shows the day under Lige nu's
    headline, each topic's line under its headline ('Bygger på …'), 'I nyhederne' under the figures, 'Det kommer' in Lige
    nu (a tap opens the Kalender tab at it, `khabarOpenCal`) and its statement as 'Dagens citat'. Public prompt:
    docs/hjerne/routine-okonomi-prompt.md.
  - `trig_01A5Nc5cQACxsN2mpYAqymwE` caretaker: daily 04:30 UTC, repairs/disables feeds in config/feeds.json,
    appends a line to docs/radar-status.md.
- Phones sign up themselves: the app posts {kind: sub|unsub, sub, want} to the relay; `push.py` keeps them in
  `state/phones.bin` (Fernet, key from PROFILE_KEY). The old `PUSH_SUBS` secret is still merged in (every kind).
  `want` is the reader's own choice of kinds (the settings' three switches: `top`, `digest`, `svar` – a new answer of
  Hizb ut-Tahrir's, `analyses.to_tell`, never at night); a phone from before the switches gets top and digest;
  `everyone(phones, kind)` filters. A notification's link carries `&n=1` (the statistics tell it from a shared
  `?item=`). Test with `gh workflow run push-test.yml` (it prints the phones per kind).

## Project-specific conventions

- The owner wants it **fully automatic**: no feedback buttons. Adaptation comes from community
  sources, big stories and silent share/copy/open signals only.
- The one exception is the owner's hidden admin (2026-10-11): hold the logo 1.5 s → admin code (own sheet, no prompt()); hold a story → remove
  (irrelevant / not news / duplicate) or move – since 18/10 any element: a comment to the editors, his own headline, the
  picture, priority, section, Dagens historie, removal. No visible button – the owner asked for a long press. Actions are
  HMAC-signed with ADMIN_KEY (`scripts/setup-admin.ps1` makes it; never ask for or handle the code), checked in
  `src/radar/admin.py`, kept in `state/removed.json`; the editor's input lists them.
- Sharing is one action inside an opened story (Læs, Del, Kopiér), not the centre of the app. Motion stays quiet
  and functional: no skeuomorphic paper/ink effects (the owner found the stamp and ink drop unserious).
- **One thing open at a time (a strict rule, the owner 18/10):** opening a story, an event, a tile or a row closes
  whatever else is open, on every page; while it is open the rest of the page is dimmed, and a tap outside it only
  closes it – it never opens what lies under the tap (app: `focusSync`/`closeOpen`, a `.dim` layer; Økonomi: `sole`,
  `focusSync`, `.dimmed`).
- **The app (2026-10-17, the owner's decision; the fifth tab 2026-10-18; the map shelved for the calendar 17/10): five
  tabs, Forside · Live · Kalender · Økonomi · Analyser** (Danmark, Mellemøsten and Verden are gone; Kort was a tab from
  17/10 until the owner shelved it the same day: "meget mere taktisk, end det er strategisk … Så synes jeg godt, vi kunne
  have en kalender i stedet for den … Og den skal have en fane for sig selv"; `?tab=kort` opens Forside).
  **The options dock (18/10, the owner: 'man skal let med tommelfingeren kunne trykke frem og tilbage på de der
  forskellige knapper eller valgmuligheder, der er under hver side'):** a page's own options sit right above the tab bar,
  never as a strip under the top bar – the top bar keeps only the logo and title, Gemt, search and settings. One shared
  component, `#opts` inside the fixed `.dock` (`paintOpts(t)`, `dockTab`; Live `liveOpts`, Kalender `calOpts`, Analyser
  `anOpts`; none on the front page, side pages and search): one or two `.o-row` rows of chips and segments that slide
  sideways when they overflow (`touch-action: pan-x`), patched with `morph` so a row keeps its place, solid like the bar
  (no blur), gone while the keyboard is up (`.keyboard .opts`); it follows the page in view during a swipe; its
  buttons go through the same handlers as the pages' (`onTap`). Its height is part of `--dock` (the
  ResizeObserver on `#dock`), so the pages' foot room, the toast and `keepInView` (an opened story's buttons come up
  above it) count it. Analyser's search field stays under the bar (the dock goes with the keyboard; the field must
  not). **Kalender** (`kalenderPage` and its section in app.js, its section in style.css, tests/test_calendar.py): the
  radar's calendar.json (`CFG.calendarUrl`) and the editor's kalender.json (`CFG.kalenderUrl`; a 404 until the first
  entry) merged by `calItems` – the editor's entry wins on the same date and title, or its id – fetched with the news's
  reload (`VFRESH` cal 30 min, kal 10 min; an unchanged file draws nothing; the page's `SIG` holds its choices). In the
  front page's Economist manner: a red fly title 'Kalender' and one Source Serif 4 line naming what comes next ('Næste:
  Midtvejsvalg i USA om 17 dage'), then 'Det sker snart' (the next seven days with 'i dag', 'i morgen', 'om 5 dage',
  'i gang'), then month by month under sticky month headers, and 'Tidligere' (the last 30 days) folded at the foot. A row:
  the day large in tabular figures and the weekday small (a month only: its name), the title, one quiet line – the
  kind with its calm dot (`--c-valg` … each light and dark; red only for an event today or tomorrow, `.ck.near`), the
  place, 'til …', 'forventet' –; a tap opens it in place (one at a time): the why, 'Kilde ›', Del · Kopiér and up to three
  stories in Live that name it (the editor's ids, else the place and a title word, or two title words). The dock: Alle ·
  Valg · Topmøder · Centralbanker · Frister · Danmark (for the visit) and, first, 'Kun vigtige' (remembered, `calImp`; the same chip in Live, `liveImp` – it hides what is of low weight, and the page says what it hides with 'Vis alt'); no window of months since 18/10: everything ahead is shown.
  The front page: 'Det sker snart' – the next three or four events of the coming 14 days – after the second block drawn
  (`calBlock`; composed and fixed page alike; none in the fortnight: no block), 'Alle ›' to the tab, a row opening the tab
  at its event. A share: '17/10 · Midtvejsvalg i USA – <why> – via khabar.nu/?kalender=<id>'; `?kalender=<id>` opens the
  tab at that event (opened, the filter and window widened to hold it, aimed below the bar and its month – again after the
  late rows and the serif settle, `calAimAt`). **Økonomi** (`okPage`): `energi/?embed=1` in a same-origin frame filling the page between the bar and
  the dock, made when the tab is first shown or a swipe heads for it: the economy page hides its bar and back link and
  follows the app's look and text size live (it watches the app's `<html>`; the page itself is another agent's work –
  `public/energi/`). The oil row of an opened story and Indstillinger's 'Mere' open Økonomi (`data-okonomi`,
  `openOkonomi`); `?tab=okonomi` opens the tab and `?tab=priser` is kept as its alias; khabar.nu/energi stays a page of
  its own.
  The look stays as khabar.nu. **Live** is the stories the radar admits at the editor's level (app.json; data.json
  filtered by its `live` marks when app.json is missing; since 17/10 three chips Danmark · Mellemøsten · Verden filter it
  for the visit) – since 18/10 ONE list, newest first (no Seneste/Vigtigste: the owner, 'Nyheder skal have én fane'),
  each row showing its weight as the calendar's (`weightOf`: 'Høj betydning' – the former 'Topnyhed', topNow's five –
  on a soft red ground with a red edge; middle – big, an editor's pick or the books' tiers 1–2 – a short red mark under
  its time; the rest quiet), each row with its small section dot; the owner's long-press 'move' sets the
  dot and the Danish lift. Old links (`?tab=dk|me|world`, a notification's `?item=`) open Live. **A story's headline**
  (round 2): the editor's (summaries.json `titles`, matched by the card's id, a member or another outlet's article; one
  the app's `curious` flags is skipped), else the outlet's in Danish where the phone shows Danish; a plain curiosity
  headline gives way to the teaser's first sentence (cut at its main clause or a word, ≤ 120 characters) or another
  outlet's plain headline; the opened story names the original in its one credit line ('Original: »…«'); an editor's 'X: …' that names the row's
  own outlet, or a news outlet that does not carry the story, loses the name (the meta line says the outlet once), one
  naming another outlet that carries it shows that outlet, and a government, state or person stays as who speaks
  (`outletKey`, `NEWS_GROUPS`). **The front page the editor
  composed** (front.json, round 2): its blocks in its order with the app's own pieces – top (the Dagens historie card:
  since 17/10 the story's own full-size picture (`pic`, never the small copy or an initials tile) across the panel, 16:9 and at most 40 % of the screen since 18/10,
  the headline and its line in white on a dark fade at its bottom, in the press photo look (15 % colour, 30 % opened,
  film grain – the owner's choice), `leadPicFailed` remembers a failed one in `badPics` and leaves the text lead; none: a
  text lead; `picture: false` holds only for a second main story – then its timeline's two newest updates and 'Hele
  udviklingen ›', one `with` story and the answer line), liste (three stories, a quiet Danish one two, the rest behind
  'Alle ›', which unfolds them in place; `billeder`: the first story with a picture large), udvikling (three), citat
  (one), svar, live (the newest stories no other block shows), linje; at most six blocks after the lede (`FRONT_MAX`);
  a story once; a block whose stories left Live is skipped (the first main block drawn carries 'Dagens historie'; none
  left: the day's main story leads); the owner's pinned main story and quote win. **Denmark only when it matters** (the
  owner, 17/10: "danmark er ikke så vigtig … medmindre det er vigtige historier"): a list whose stories are all Danish
  and none big, held by Live as Danish politics on Islam and Muslims (`live: 'dk'`) or among the day's five strongest
  (`dkMatters`) is cut to two rows and set after the other blocks (`frontOrder`). Missing, unreadable, empty, older than
  6 hours between 06 and 24 or 12 at night → **the fixed front page**,
  organised by story and time: date + the editor's lede, 'Dagens historie' (the recap's lead topic matched to a top story
  by shared words: its picture, timeline, a quote from it), 3 more top stories (never the main story again), 'Danmark'
  (two rows) only when a Danish story matters, 'Følg
  udviklingen' (the 3 developments that moved last, not the main story's), 'Dagens citat' if the package had none, 'Live'
  (the 3 newest Live stories); no section glance, no recap, **no analysis**. **The lede's parts open their stories**
  (the owner, 17/10): cut at ', ', ' mens ', ' og ', ';' and ' – ' (a part under three words joins its neighbour;
  `ledeParts` = `editor.lede_parts`), each part a real link (`a.lede-a`, `?item=`, a thin solid underline in `--line`)
  to the editor's `lede_ids` story or the story sharing its distinctive words (names and wiki pages weigh double, words
  in more than a quarter of Live's stories count nothing; the front page's stories first, then Live; `ledeLinks`); a
  tap opens a front-page story in place, in view, else in Live; no match, plain text. One quiet line under Dagens historie – and
  in an opened story – when the amir has answered on its subject ('Hizb ut-Tahrirs svar · d/m/åååå' over the title):
  a headline subject the answer is about (its title, its question's first subject, its main issue; a filed answer's
  readings, never its whole begreber list), a second signal from the headline (another subject the answer is about, or
  two shared words; a report of the dead or one state's domestic story needs a specific subject), at most three years
  old – else no line (`answerFor`, docs/hjerne/notes-app.md; 14 of the top 90 on 16/10 after the review). **Analyser**: the amir's answers, the
  newest first (the editor's answers.json and the radar's `analyses` before the layer's 321 by year), a search field and
  a 'Begreber' row to the wiki's A–Å index; the answer reader (calmed 17/10 after the owner's "uoverskuelig"): the
  byline, the title with the question under it, one ochre panel ('Svaret kort' and what it reads), its concepts, the
  answers it cites and that cite it, the text when held (folded). **The wiki**: a concept named in plain text – an opened
  story's headline and summary, the recap lines and the lede on Udvikling, an answer's note (not the front page's lede,
  timeline or line since 17/10) – links its page
  (`public/viden/begreber*.json`): the first mention, at most three a block, a dotted underline in the text's colour,
  never Danmark and never inside an outlet's name. **A link is never inside a button**: a row's button or link lies under
  the whole row (`.hit`) and its words on top let the tap through. A wiki page: the lead (the newest answer governs),
  'Gennem årene', relations, the answers, related pages, today's stories that name it. **Everything that is Hizb
  ut-Tahrir's** (leads, timelines, notes, readings, answer texts, the answer lines) is set in the serif (`--serif`) and
  marked by a thin warm rule at its left (`--ht-rule`) – since 18/10 on the page's own ground in the page's own text
  colours (the owner: 'den gule baggrund … gør det svært at læse'; the ochre tint `--ht-bg` is gone, the `--ht-*`
  tokens equal the page's; the answer reader's question is serif in `--text-2` inside the header its byline labels); every such block carries ONE label with the name and
  date ('Hizb ut-Tahrirs svar · d/m/åååå': the answer line, the reader's header, a wiki lead's `htLabel`), a block of
  several answers' texts (the wiki's timeline and relations) a small date on each row (`htDate`), and the texts
  themselves never say 'Ifølge …'; everything else keeps the app's face.
  **Side pages** over the tabs, reached from a button or link and left by a tab or the logo with its back mark (which goes
  back the way one came, scroll kept; the phone's own back gesture does the same – each side page is a step in the
  browser's history, and the address names the page in view): Udvikling, an answer, a wiki page, the A–Å index. The **Udvikling** page holds
  the editor's lines once (2026-10-11 the owner had the recap and the developments merged – as two views they clashed):
  'I dag' with 'Resumé kl. …', the count of updates and 'Del resumé' (the WhatsApp text), the lede whole; the day's developments in the editor's
  order, each a card with its lines of the day, newest first, that unfolds into the whole development across the days
  ('Hele forløbet'); then 'Fulgt de seneste dage'; then 'Tidligere dage' (whole recaps, to read or share). A development
  tapped elsewhere opens unfolded; the recap notification (?digest=1) opens the page at the top. The name is 'Live'
  everywhere. Foreign headlines show in Danish by default (the editor's checked Danish first, else the machine's; the
  opened story names the original). The intro plays on the first visit and after six hours away, else the app opens
  straight in; a link into the app (`?item=`, `?svar=`, `?begreb=`, `?forlob=`, `?digest=`, `?tab=`, `?gemt=`) skips it.
  Text size follows the phone (iPhone Dynamic Type) or the setting: app.js sets `--tsu` on `<html>`; the pages use it
  whole, the bar, the tabs, the search field and the sheets capped at 1.2 (`--ts`); every font size is one of eight
  tokens `--fs-cap/meta/small/body/read/lead/block/title`, each `calc(Npx * var(--ts, 1))` (exempt: the logo and the
  intro's mark, the initials tiles, the tab label, the owner's statistics – tests/test_app_speed.py). Old news: only
  the box on the page, the top bar stays quiet. Shared texts end with 'via khabar.nu/?item=…' (or ?svar=, ?begreb=,
  ?forlob=), so the recipient lands in Khabar. Bump `?v=` on every change: the service worker serves versioned files
  from its cache.
  Colour is minimal (the owner found section-coloured labels 'in your face') – except the front page's red accents since
  17/10 ('Forsiden bliver for monoton, brug gerne lidt rød og flere nuancer': the date, a bar before each block title, the
  newest step, the ways on, the quote; `--red`, readable in both looks, only under `.page.fp`): a small section dot on mixed lists, red
  only for big stories and 'live', the ochre only for the movement's text. Headlines guide the eye with bold keywords
  (who and where) instead. Block titles and day markers must never look alike.
- **Speed rules (round 2, measured 2026-10-17, docs/hjerne/notes-r2-speed.md and notes-r2-review.md):** a reload
  patches the page (`morph`: rows keyed by `s-<id>` keep their elements) and keeps the row being read in place; every
  redraw from a reload waits while a finger is on the screen or the page still moves (`renderSoon`, `drawSoon`,
  `redrawPages`); a file the same as last time is neither parsed nor drawn; the phone keeps its copies as the text it
  received, in idle time; dates through the formatters made once (`FMT`); a card whose lead article changes is carried
  over to its new id (`carryOver`: opened, seen, shared, its row renamed in place); a picture that failed is remembered
  (`badPics`) and one loaded in view is drawn without `loading="lazy"` after (`nearPics`), so a patch never undoes
  them; side pages hide the tabs behind with `content-visibility: hidden`, rows out of sight `content-visibility: auto`;
  no `backdrop-filter`, no blend modes, no animated filter/height/top/box-shadow/background-color, only transform and
  opacity, Reduce Motion respected (tests/test_app_speed.py holds these). A closed headline gets up to four lines and
  its row grows (no fixed row height); `contain-intrinsic-size: auto` remembers a row's real height after its first
  layout, so rows out of sight keep their place.
- **Content rules for every Danish text Khabar writes** (the editor's lede, lines, summaries, titles; the app's words;
  the wiki's pages): Israel in our own voice (the movement's term only inside a quotation) – in the editor's text in the
  owner's house style (2026-10-17): lower case inside curly quotes, every form (“israel”, “israels”, “israelske”),
  written so by `voice.quote_israel`, which `editor.py publish` applies to every file it writes (`quoted`), and in the
  app by `quoteIsrael` (keep the two alike) for every Danish headline and teaser it shows, the calendar's and the energy page's
  too – never the outlet's original in the credit line or Hizb ut-Tahrir's texts; no praise of or call to
  violence; judge states, rulers, policies and ideas – never peoples or religions; no claim that a non-ruling person, a
  Danish person or organisation, a mosque, a scholar or a media outlet serves a power; no conspiracy myths; the
  answers' claims that deadly attacks were staged are not repeated as such. `scripts/voice.py` checks the editor's:
  outside a quotation it refuses the channels' names for Israel ('den zionistiske fjende', 'Zionist-regimet') and a
  source's framing word in Israel's place ('Besættelsesstyrker anholder …'; beside the name it may stay: 'Israelske
  besættelsesfly'), 'martyr', 'heltemod', 'heroisk' and 'helte' near fighting.
- The app never mentions Claude in visible text and has no 'how Khabar chooses' explainer (owner's request,
  2026-10-10). The looks: Dæmpet (light) and Notion (dark) only since 17/10 (the owner: "Skær farvetemaet med til to");
  the settings choose Automatisk · Lys · Mørk.
- **Khabar made professional (2026-10-17, docs/hjerne/pro-plan.md, built in full; tests/test_app_pro.py,
  test_app_contrast.py, test_pro.py):**
  - **The front page's headline (17/10, the owner: 'Se til the Economist'):** the lede's first part in Source Serif 4
    (`--display`, Google Fonts), its rest as the rubric in the same face, the date a red fly title, a red rule over block
    titles – Khabar's headline voice; Hizb ut-Tahrir's serif stays the phone's own on the ochre tint.
  - **Two voices:** the app's sans is Khabar's and the outlets' voice (the lede, block titles, development names, an
    outlet's quote in italic sans, the intro); the serif only Hizb ut-Tahrir's (`.ht*`, `.an-*`, `.rd-*`, `.wk-*`).
  - **Red** only for live and big: one red dot on the front page (its Live block, `blockHead(title, more, live)`), the
    Live tab's dot; 'Høj betydning' (the former 'Topnyhed') on at most five stories at a time by `topScore` – the
    editor's first three picks 4, another pick 3, the books' heaviest tiers (1–4, 6) 2, a big story (coverage) 1; two
    points needed, so coverage alone never does it (the owner, 18/10: 'stor dækning burde vægte mindre end redaktørens
    valg eller bøgernes tungeste katagorier'); a pick holds 24 hours, the rest twelve, by hours not the calendar day;
    never in a chosen block (`topNow()` in `meta()`; `run.top_score`/`top_now` the same for the notifications); the lede's date and the day pill
    are quiet (`--text-3`, `--fill-2`). Dark segments and chosen chips: a step lighter (`--seg-on`). No other red:
    the old-news and offline box is a grey panel with its icon, search marks bold on grey, switches and the focus ring the
    text colour, the logo's dot grey while the news are old or the phone offline, a failing source a hollow dot
    (tests/test_app_pro.py fails on `--pulse` elsewhere). Every text colour is ≥ 4.5:1 on the page and on a panel in all
    eight palettes.
  - **Rows keep their words:** four headline lines, the row grows; the meta line (`Kommentar` or `Topnyhed`, the section
    on mixed lists, the outlet, the time, 'N medier' from three outlets on – one rule everywhere) breaks between its items and never starts
    with '·' (each item carries its dot, the line's first is clipped away); a list of one section drops the section
    word, a list of mostly one names it only on the others (`mainSec`, `opts.msec`); a new story's dot sits before its
    time. One separator rule: 16 from the left, to the right edge. One spacing scale (4–32), radii 12 (buttons, the answer line, quotes), 16 (panels), 20 (sheets), 1 px
    separators; a panel sits 12 from the edge with 12 inside. One of each component: `blockHead(title, more)` with its
    right-aligned 'Alle ›', the quiet text button `.qbtn`, the quiet row `.qrow`, chips 36/44, minis 40/44, segments 44,
    `.grp` group headers (search, A–Å, settings) that never look like a day pill, `stateBlock(kind, text, actions)`.
  - **States:** skeleton rows at most four seconds, then 'Ingen forbindelse …' / 'Kunne ikke hente …' with 'Prøv igen' –
    the same cause the same words and icon on every page (`retry` asks `netDown()`); the boxes say the day of an old copy
    (`fromWhen`: 'fra i går kl. 21.34'); the bar: the offline mark before the copy's time, or 'offline' with no copy; a
    reload, and every file that failed again, when the network comes back;
    'Prøv igen' on an answer's or a wiki page's missing file; 'Siden findes ikke' / 'Svaret findes ikke' / 'Historien
    er ikke længere i Live' (a link's story looked for among everything the radar read) with a way on; new stories read
    aloud through `#srStatus`.
  - **Time and words:** one formatter `stamp()` ('nu', '4 min' to nine minutes, 'kl. 10.16', 'i går kl. 21.34',
    'lør. kl. 23.32', '12/10'); timelines newest first with day rows ('I går', 'Torsdag'); a development is an
    'udvikling', each of its lines an 'opdatering'; 'fulgt i 8 dage · senest kl. 10.36'.
  - **Shared is what is seen:** a story's share sends the headline shown, the first sentence of the editor's summary
    (else of the cleaned teaser), the outlet's link and 'via khabar.nu/?item=<id>'; teasers lose calls to action, links
    and picture captions (`cleanTeaser` in app.js = `clean_teaser` in src/radar/headlines.py – keep them alike); one
    credit line replaces the two notes; an answer the front page shows is not said again in a story opened there.
  - **The views:** Forside – the lede whole (the editor keeps it to about 25 words; no paragraph is a button – its parts
    are links inside it), 'Del
    overblik' (icon and word) on the date line, 'Mens du var væk' after three hours away (counts only, fades on the first
    scroll; it stores nothing new), the answer line right under the main story, its development named and opened by its
    label – the editor's timeline or the story's own development (`threadFor`) only when the development's name shares a
    specific subject with the headline (a wiki page or a word, never only Trump, Putin or the USA) or the editor filed
    the story in it (`topicFits`, `topicOf`), else none, and only such a development's name helps find the answer line, the Live block without commentary (the prices' link at the
    foot went to the Økonomi tab since 18/10), the fixed page's 'Danmark' block, the iPhone install hint once. An opened
    story: up to three ochre wiki chips, 'Udvikling: <name> ›', the bookmark, an oil row when the text names oil or fuel (it opens the Økonomi tab).
    Udvikling: its own address (`?forlob=<key>`), Del/Kopiér per card, a long course three days at a time, its name
    sticky inside it. Analyser: one title line, a strip under the bar with the field, and one chip row in the dock (A–Å, the areas as
    a filter for the visit, the years), the page a query names first, 'via <page>', the question's phrase,
    rows as links, an opened answer drawn quieter (`ansRead`, ≤ 400). The answer reader (17/10, the owner found it
    "uoverskuelig": too many boxes, labels and heavy buttons at one weight): the byline ('Hizb ut-Tahrirs svar ·
    d/m/åååå', the area, 'Originalen ›' – the page's ONE label, so nothing under it carries another), the title, the
    question right under it as plain serif text in `--text-2` (`.rd-q`: no box, no label, no tint), Del · Kopiér · Gem as
    one quiet row of small buttons (`.know-acts`: icon and word, 40 px seen and 44 to the finger, left, not stretched –
    the wiki page shares it; a story's own row is unchanged), then ONE ochre panel (`.rd-ans`): 'Svaret kort' with its
    paragraph, then each reading under a `--ht-line` hairline, its subject a small bold line linking its page (no
    'Hvad svaret læser' heading, no box per reading); under it one quiet row 'Nyeste svar om <område>: <titel> · d/m/åååå
    ›' (`.qrow`); 'Begreber' (four chips, then '+ N'); 'Svaret henviser til'; 'Senere svar, der henviser hertil'; 'I
    nyhederne nu'; a held text ('Svaret på engelsk') folded behind 'Læs hele svaret ›'. No 'Åbn originalen' button: the
    byline's 'Originalen' is the way to the source (tests/test_app_pro.py). A wiki page: a contents row, the paired page (a state and its issue), Del · Kopiér · Gem, today's news
    under the lead, 'Gennem årene' under its one label as rows under their years, each row's small date the way to its
    answer, without the lead's own; a shared answer or page carries the label too. A–Å:
    six groups as one chip row (Stater · Aktører – magt, gruppe, organisation – · Steder · Sager – sag, proces – ·
    Begreber · Aftaler: every page in one), the most used pages, a state's issue under it, the letters sticky. Tabs: Analyser stays selected on
    its side pages; a tap on the tab of a side page goes back to its list. Settings (cleaned up 18/10, the owner: 'Ryd
    gerne op i indstillinger siden'): the owner's block first ('Kun for dig': the chief editor's report, the senior and
    chief editors' notes from memo.json – four lines each, whole at a tap, `notesHtml` –, the statistics), then
    Notifikationer (three switches), Visning (text size; light or dark), Sprog (Danish headlines; Arabic and Turkish),
    Kilder (one row – 'N kilder', how many do not answer – that unfolds the list) and 'Læg Khabar på telefonen' with the
    offline library's line; no repeated link to the Økonomi tab. Accessibility: tab panels, the pages not in view
    `aria-hidden`, a row's label read once, headings for days, years, letters and sections.
  - **New functions:** Gem (`localStorage 'saved'`, ≤ 200, written in idle time, nothing sent anywhere: a story's
    snapshot – so it opens offline and after it left Live –, an answer's number, a page's id; the side page 'Gemt',
    opened by the bookmark in the top bar – filled once something is saved – and the save toast's 'Se Gemt' (since
    18/10: Analyser, then Nyheder, then Begreber, each a quiet row with ONE filled bookmark at the right that takes it
    out; the list read leniently with a second copy `saved-bak` and `storage.persist` asked for, so no update loses it;
    'Del eller flyt dine gemte' at the foot makes a link with the saves in its #fragment – never sent to a server –
    which, opened on another phone or by someone else, asks 'Tilføj til mine gemte' or 'Erstat mine N gemte':
    `moveLink`, `takeMove`, `useMove`); the library – movement.json and begreber.json – fetched once per build of the wiki (`libFor`),
    in idle time after a visit to Analyser, not parsed until a page needs it, not on save-data or 2g); one search with
    scopes Alle · Nyheder · Svar · Begreber – the news first, five stories under Alle, the answers named in their title
    first, words matched where they start (the last five searches on the phone); Mens du var væk; Del dagens overblik
    (one story from each of the editor's blocks in the page's order, then the blocks' next ones, at most five; only the
    editor's checked headlines or a Danish outlet's own plain headline – never a machine translation, a teaser standing in
    or a curiosity headline –, no commentary, links without tracking tails); notifications by choice (a choice that
    could not be sent is kept as `wantDirty` and sent when the phone is online, comes back or starts; a phone from before
    the switches sends its choice once). Text selection (the owner, 17/10): only
    reading text – a summary, the lede, the movement's texts (`READING` in app.js = the rule in style.css) – never a row
    or a button, and the owner's long press skips it. Waiting (the owner's call): following a topic, picture share cards,
    
- **No machine translation from Arabic, Turkish and the like reaches a reader** (18/10, the owner: '… burde kun tages
  med når redaktørerne har gennemgået oversættelserne. i dag er de for svage'; and then 'engelsk til dansk
  oversættelserne var gode nok, så dem beholder vi' – English keeps the machine's Danish): `display` shows such a story with the editor's
  headline, else a Danish outlet's own headline (`also`, lang da), else marks it `held` and `stories()` leaves it out
  until the editor writes one; no machine teaser as a summary; the coverage list and search show the outlets' own words;
  Økonomi's `reviewed` – which since 19/10 holds English back too (the owner: 'Økonomi sidens nyhedshistorie titel
  oversættelser er elendige og bør gennemrettes af redaktøren inden udgivelse'), and the page's stories are in every
  editor's 'Headlines to write' (`editor.economy_shown`, `with_economy`); `run.push_headline` returns '' for such a story and the notification waits in `pending`; the
  economy editor's stories need a Danish headline (`okonomi_file(titled=…)`). The radar still translates – for the
  editors' input and the matching – and a reader who chose the originals sees them.
- Danish politics must never be buried **in Live and the radar**: keep the Danish lift (`rank_core_dk`), `protect_dk`
  and the dk-section rules when tuning the rank. The front page is another matter since 17/10: Denmark there only when
  it matters (a big Danish story, Danish policy on Islam and Muslims, Denmark's place in a great power's plan – the
  editor's prompt and `brain.RULES`; the app's `dkMatters`). Before changing thresholds or word lists, run `py scripts/rank_check.py` (one radar pass on a
  copy of the live state, no fetching or embedding) and compare what Live (one list, with the method's tiers) and each
  section would show.
- The profile contains no names or message authors. Keep it that way, and keep it encrypted. The repo is public.
- **The answers' whole English text is published** (the owner's decision, 17/10: "hele teksten fra analyser … på
  engelsk", asked whether the texts may lie in the public repo: "Offentligt, som de er"): `scripts/build_fulltext.py`
  writes `public/viden/svar-en/<nr>.json` (and `index.json`) from the local HT archive's English texts (272 of 321);
  the answers the archive has only in Arabic are translated into English, faithfully and whole, and marked
  `translated: true` ('oversat fra arabisk' in the reader). The reader fetches a text only when 'Læs hele svaret
  (engelsk)' is unfolded. This replaces the earlier rule 'no full answer texts in committed files' for these texts.
- Facebook, Instagram, TikTok and X cannot be followed. Do not add scrapers for them without the owner's explicit decision (cost/ToS risk).
- Tests use `tests/fake_embed.py` instead of the real model, so they run offline without fastembed.

<!-- Anything that differs from, or adds to, the workspace standard. If nothing
     differs, say so explicitly so the next session does not go looking. -->

## Constraints and gotchas

<!-- Things that will bite someone who does not know them. External services that
     must be running, ports in use, data that must be seeded first, known-fragile
     areas. Add to this list every time you hit one. -->

- **A preview of changed app code needs the service worker passed by**: it serves `app.js?v=…` and `style.css?v=…`
  from its cache under the same version, so an edit without a new `?v=` does not show in a browser that ran the app
  before (DevTools: bypass for network, or a fresh profile).
- **Headless Edge's `--window-size=430,…` lays the page out wider than 430 px** (Edge's minimum window width) and cuts
  the right edge off; for exact phone shots drive headless Edge through the DevTools protocol
  (`Emulation.setDeviceMetricsOverride` 430 × 932 at 2x, `--remote-debugging-port`, Node's own WebSocket).
- `answers.json` does not exist on the digest branch until the editor files the first new answer: the app's request for
  it gets a 404 (taken quietly, asked again after ten minutes).
- **The full English text of a new answer** sits in `state/analyses.json` on the public data branch (the editor
  routine has no internet) and the answer reader shows it ('Svaret på engelsk') until the next build of `public/viden`.
  Whether that is within 'no full texts of the movement's answers in committed files' is the owner's call (open since
  2026-10-17): the alternative is to encrypt the text with a key the routine holds and show only the byline's 'Originalen'.
- **`Path.write_text` on Windows writes CRLF** (text mode turns '\n' into '\r\n'): patch scripts write with
  `write_bytes(s.encode('utf-8'))`; check `git diff --stat` for whole-file changes before committing.
- **Heredocs through the agent's Bash tool lose backslashes** (a doubled backslash arrives single, so a regex's back-reference
  becomes a control character and a word boundary a backspace): write files with regular expressions through the Write
  or Edit tool, not cat or py heredocs, and scan for control characters after an edit.
- The wiki's issue leads are written by hand, newest first, in `scripts/begreber_leads.py` (from the issue's own
  history, in the attributed working form whose first sentence carries its answer's day – that day picks `lead_nr`);
  `build_begreber.py`'s check fails when an issue's newest main answer, or any page's newest reading, is newer than its
  lead, or when a shown text still names the movement.
- **No 'Ifølge Hizb ut-Tahrir' in a shown text** (2026-10-17): `docs/hjerne/uden-ifolge.json` maps every text as the
  builds wrote it (attribution and all) to its plain Danish form, and both builds apply it last. A new or changed
  reading without an entry loses only the 'Ifølge Hizb ut-Tahrirs svar af d/m/åååå: ' the build put in front; one that
  still names the movement ('Ifølge svaret …', 'Hizb ut-Tahrirs svar læser …') fails the check – add its plain form to
  the map (V2 word order: 'Ifølge svaret er X …' → 'X er …'; a span of answers in brackets at the end). The editor's
  new answers are written plain from the start (`voice.check_plain`).
- The wiki is a build: edit `docs/hjerne/begreber-ideer.json` (concepts) or the movement layer's inputs, never
  `public/viden/*.json` by hand, then `py scripts/build_begreber.py` and commit both wiki files.

## Definition of done

A change is finished when:

1. Tests pass.
2. `CHANGELOG.md` has an entry under `## [Unreleased]`.
3. `.project.json` has an updated `updated` date.
4. `README.md` still describes reality.
5. The work is committed with a Conventional Commit message.
6. The owner has been told what changed, in plain language.
