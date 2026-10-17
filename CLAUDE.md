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
answers appear only as his, attributed ('Ifølge Hizb ut-Tahrirs svar af d/m/åååå …') and in their own face. Concepts
named in the news open a wiki page compiled only from those answers. Claude looks at the site every quarter of an hour
(`editor.py check`) and updates what needs it ("der er tokens nok"). The users are young Danish Muslims who use the news
in their da'wah.

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

- `src/radar/feeds.py` fetches and parses every source type (rss, gnews, telegram, youtube). Stdlib only.
- `src/radar/run.py` is one radar run: dedupe → embed → self-learn → score → cluster (+ second look at cards)
  → sections and rank → show/important/big → translate → notify → write state, `data.json` and `search.json`.
- `src/radar/sections.py` places stories in dk / me / world and gives the word signals (core, core_dk, trivia,
  local, named) used by the rank; the word lists live in `config/sections.json` (format explained in its `_help`).
  Every source in `config/feeds.json` has a media `group` (dk, west, mena, il, east, official, channel, bevægelsen), a
  `camp` (the state or bloc whose view it carries) and some a section hint `sec`;
  `label` is the readable name the app shows, `official` marks a news outlet's own Telegram channel (not an
  unverified channel) and `wire` a one-line statement feed (Al Jazeera urgent: counts as an outlet, feeds
  `lines.json` and the Bevægelser briefing, never a card of its own). `"scale": false` marks a source added for its
  camp (31 of them, 2026-10-17): it never moves the established sources' scale (taste percentiles, a section's bar,
  the outlet lift, big stories) and leads at most `max_added_per_day` (config/settings.json, 3) cards of its own a day,
  and only stories no established source carries. The movement's own outlets (group `bevægelsen`) never count as an
  outlet or confirmation, and governments' channels (`official`) never lead a story others carry.
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
  `movement.json` and `movement-index.json` (the 321 political answers 2004–2026 as dated, attributed Danish readings);
  `scripts/build_begreber.py` → `begreber.json` and `begreber-index.json` (203 pages: states, powers, groups, issues and
  the concept pages of `docs/hjerne/begreber-ideer.json`; aliases are Danish news forms, never an adjective, a people's
  word or a capital for its government). A test fails when the committed wiki is not a fresh build.
- `src/radar/thumbs.py` gives every card a small picture (feed image → another outlet's → the og:image of the lead's
  article page, then of up to four other outlets' pages; a story without one shows its outlet's initials in the app –
  the owner likes those tiles and declined pictures found by the editor, 2026-10-11),
  shrunk with Pillow to a 144 px JPEG in `state/t/` (served from the data branch); unverified Telegram channels
  never lend one. `state/pics.json` remembers page images and failed pictures for 3 days.
- `src/radar/push.py` sends Web Push; `src/radar/feedback.py` reads copy taps from the ntfy.sh relay.
- `src/radar/stats.py` keeps the owner's statistics (2026-10-11): the app posts `visit` (home screen or browser, iPhone/Android/other, time zone, language, how it came; `first` on 'Kom i gang') and `leave` (seconds, tabs, stories opened) to the relay; read/share signals give the most read stories (the owner's own carry `me` and are not counted). Counts per Danish day in `state/stats.enc`, AES-GCM with a key from ADMIN_KEY (sha256('khabar-stats|' + code)); the app decrypts it in the admin-only block at the top of Indstillinger. Nothing is stored on phones and no id follows a person – the owner declined anonymous ids for unique visitors (2026-10-11: consent rules) and wants no consent prompt or button, so place in Denmark is not collected (it would need a permission prompt or an IP lookup); country comes from the time zone.
- `scripts/editor.py` is the Claude editor's tool (check / input / publish, see its docstring). `check` is the
  quarter-hour look (≤ ~40 lines, verdict INTET NYT AF VÆGT or OPDATÉR: why); `input` carries the brain
  (`scripts/brain.py`: the order of weight and each power's current reading, ≤ 6,000 characters) and the front page
  now; `publish` keeps what a small update leaves out (lede, picks, quotes), checks the editor's text with
  `scripts/voice.py` (the content rules; reality only, never the movement's reading as fact) and files a new answer in
  `answers.json`. It keeps one overview per
  Danish date: each update adds short 'Who: what' lines to the day's topics (newest first); the day lists every
  wire line id its updates were given (`ids`), so the next update gets only new ones. Old edition archives
  (`briefs`) are folded into days automatically.
- `src/radar/energy.py` (2026-10-17, owner's request: an OSINT page for oil, fuel and the real market) writes
  `energy.json` for `public/energi/` (khabar.nu/energi) after every radar pass, stdlib only, a step in radar.yml that
  may fail without stopping the save. Sources: Yahoo Finance chart API (futures, contract months for the curves,
  USD/DKK), FRED CSV (EIA spot; FRED drops a browser-like User-Agent, so it gets a plain one), Circle K's public
  price API (header X-App-Name: PRICES; Circle K + INGO) and q8.dk/Station/GetStationPrices (Q8 + F24). Each source
  has its own clock (EVERY) and keeps its last good numbers; pump prices keep one point a day for 400 days. The
  page holds all names, units and explanations; the file only numbers.
- `public/` is the PWA. `config.js`, `data.json` and `dev/` there are local-preview only (gitignored);
  `pages.yml` generates the real `config.js` (data, digest, search, moves, answers, analyses and energy URLs).
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
    om der er noget, der skal tilrettes. Der er tokens nok"):** four routines with the same prompt
    (`docs/hjerne/routine-prompt.md`, the private weighing guide inserted at `[WEIGHING-GUIDE]`) on cron `0 * * * *`,
    `15 * * * *`, `30 * * * *` and `45 * * * *` (a routine fires at most hourly). Each starts with `editor.py check` and
    stops with one line unless something of weight happened; then `input`, a small update and `publish --push` (which
    refuses when another update landed meanwhile). About three to six times the tokens of twelve updates a day
    (docs/hjerne/cadence.md). The owner creates them at launch and retires the twelve-a-day routine below.
  - `trig_01B5p6DmEx8pz9cDLZzwxbHj` editor (until the launch): fires twelve times a day (since 2026-10-11, the owner's choice, ~1/10 of his plan):
    06, 09, 12 and 14-22 UTC = 07, 10, 13 and every hour 15-23 Danish winter time (an hour later in summer); each update
    is small – only what is new since the last; the app says the recap is 'opdateret løbende fra morgen til aften'. It has NO internet (the cloud sandbox blocks it; the owner
    chose not to open it): everything comes from `editor.py input`, kept lean for tokens (40 top stories, yesterday's
    recap only as topic names after 10, stories listed once, 6 summaries per update with readers' opened stories first from
    learned.json, 8 headlines). It runs
    `scripts/editor.py input`, then writes one update: picks (stories that matter most geopolitically; for Danmark,
    those useful in the group's dawah), moves (stories in the wrong section), quotes (best statements, in Danish) and
    summaries (2–3 Danish sentences for up to 6 stories from headline, teaser and other outlets – always `paywall:
    true`, and the app says the summary rests on the headlines and introductions), titles (its own Danish for up to 8 of the strongest foreign
    headlines, which the app shows instead of the machine's), recap lines (at most 5 'Who: what' lines, filed under the Danish
    date they happened; a topic continued across days is a development on the app's Udvikling page), and runs
    `scripts/editor.py publish --push` → `digest.json` (the day shown + `editor` notes the app applies), `moves.json`
    (30 days), `summaries.json` (summaries in `items`, checked headlines in `titles`; 4 days) and `answers.json` (the
    amir's answers filed after the static layer, with Danish readings and begreber ids; kept forever) on the orphan
    `digest` branch. Only the first update at or after 21 Danish time notifies the phones.
    The routine prompt also holds the owner's WEIGHING guide (what matters most geopolitically, from his own reading; it orders the lede, picks and topics, never the wording). It lives only in the private routine prompt: keep it out of this public repo.
  - `trig_01A5Nc5cQACxsN2mpYAqymwE` caretaker: daily 04:30 UTC, repairs/disables feeds in config/feeds.json,
    appends a line to docs/radar-status.md.
- Phones sign up themselves: the app posts {kind: sub|unsub, sub} to the relay; `push.py` keeps them in
  `state/phones.bin` (Fernet, key from PROFILE_KEY). The old `PUSH_SUBS` secret is still merged in.
  Test with `gh workflow run push-test.yml`.

## Project-specific conventions

- The owner wants it **fully automatic**: no feedback buttons. Adaptation comes from community
  sources, big stories and silent share/copy/open signals only.
- The one exception is the owner's hidden admin (2026-10-11): hold the logo 1.5 s → admin code (own sheet, no prompt()); hold a story → remove
  (irrelevant / not news / duplicate) or move. No visible button – the owner asked for a long press. Actions are
  HMAC-signed with ADMIN_KEY (`scripts/setup-admin.ps1` makes it; never ask for or handle the code), checked in
  `src/radar/admin.py`, kept in `state/removed.json`; the editor's input lists them.
- Sharing is one action inside an opened story (Læs, Del, Kopiér), not the centre of the app. Motion stays quiet
  and functional: no skeuomorphic paper/ink effects (the owner found the stamp and ink drop unserious).
- **The app (2026-10-17, the owner's decision): three tabs, Forside · Live · Analyser** (Danmark, Mellemøsten and Verden
  are gone; a fourth tab – live world data, made in another session – may join: a tab button, a page and `SWIPE_TABS`).
  The look stays as khabar.nu. **Live** is every story of all sections, sorted 'Seneste' or 'Vigtigste' (the editor's
  picks, then rank; remembered per phone), each row with its small section dot; the owner's long-press 'move' sets the
  dot and the Danish lift. Old links (`?tab=dk|me|world`, a notification's `?item=`) open Live. **The front page**,
  organised by story and time: date + the editor's lede, 'Dagens historie' (the recap's lead topic matched to a top story
  by shared words: hero, timeline, a quote from it), 4 more top stories (never the main story again), 'Følg
  udviklingen' (the 3 developments that moved last, not the main story's), 'Dagens citat' if the package had none, 'Live'
  (the 3 newest Live stories); no section glance, no recap, **no analysis**. One quiet line under Dagens historie – and
  in an opened story – when the amir has answered on its subject ('Hizb ut-Tahrirs svar · d/m/åååå' over the title):
  a headline subject the answer is about (its title, its question's first subject, its main issue), a second signal,
  at most three years old – else no line (`answerFor`, docs/hjerne/notes-app.md). **Analyser**: the amir's answers, the
  newest first (the editor's answers.json and the radar's `analyses` before the layer's 321 by year), a search field and
  a 'Begreber' row to the wiki's A–Å index; the answer reader: the question, 'Svaret kort', what it reads, its concepts,
  the answers it cites, the text when held, 'Åbn originalen'. **The wiki**: a concept named in plain text – the lede, an
  opened story's headline and summary, the recap lines, the front page's timeline, an answer's note – links its page
  (`public/viden/begreber*.json`): the first mention, at most three a block, a dotted underline in the text's colour,
  never Danmark and never inside an outlet's name. **A link is never inside a button**: a row's button or link lies under
  the whole row (`.hit`) and its words on top let the tap through. A wiki page: the lead (the newest answer governs),
  'Gennem årene', relations, the answers, related pages, today's stories that name it. **Everything that is Hizb
  ut-Tahrir's** (leads, timelines, notes, readings, answer texts, the answer lines) is set in the serif (`--serif`) on the
  soft ochre tint (`--ht-bg`, contrast ≥ 4.5:1 light and dark) with its attribution; everything else keeps the app's face.
  **Side pages** over the tabs, reached from a button or link and left by a tab or the logo with its back mark (which goes
  back the way one came, scroll kept): Udvikling, an answer, a wiki page, the A–Å index. The **Udvikling** page holds
  the editor's lines once (2026-10-11 the owner had the recap and the developments merged – as two views they clashed):
  'I dag' with the day's line count, update time and 'Del resumé' (the WhatsApp text); the day's topics in the editor's
  order, each a card with its lines of the day, newest first, that unfolds into the whole development across the days
  ('Hele forløbet'); then 'Fulgt de seneste dage'; then 'Tidligere dage' (whole recaps, to read or share). A development
  tapped elsewhere opens unfolded; the recap notification (?digest=1) opens the page at the top. The name is 'Live'
  everywhere. Foreign headlines show in Danish by default (the editor's checked Danish first, else the machine's; the
  opened story names the original). The intro plays on the first visit and after six hours away, else the app opens
  straight in. Text size follows the phone (iPhone Dynamic Type) or the setting (every font size is
  `calc(Npx * var(--ts, 1))`, --ts set on #list). Old news: only the box on the page, the top bar stays quiet. Shared
  texts end with 'via khabar.nu'. Bump `?v=` on every change: the service worker serves versioned files from its cache.
  Colour is minimal (the owner found section-coloured labels 'in your face'): a small section dot on mixed lists, red
  only for big stories and 'live', the ochre only for the movement's text. Headlines guide the eye with bold keywords
  (who and where) instead. Block titles and day markers must never look alike.
- **Content rules for every Danish text Khabar writes** (the editor's lede, lines, summaries, titles; the app's words;
  the wiki's pages): 'Israel' in our own voice (the movement's term only inside a quotation); no praise of or call to
  violence; judge states, rulers, policies and ideas – never peoples or religions; no claim that a non-ruling person, a
  Danish person or organisation, a mosque, a scholar or a media outlet serves a power; no conspiracy myths; the
  answers' claims that deadly attacks were staged are not repeated as such. `scripts/voice.py` checks the editor's.
- The app never mentions Claude in visible text and has no 'how Khabar chooses' explainer (owner's request,
  2026-10-10). Default look: Dæmpet (light) and Notion (dark); the 'Blød' tone was removed.
- Danish politics must never be buried: keep the Danish lift (`rank_core_dk`) and the dk-section rules when
  tuning the rank. Before changing thresholds or word lists, run `py scripts/rank_check.py` (one radar pass on a
  copy of the live state, no fetching or embedding) and compare what Live (one list, with the method's tiers) and each
  section would show.
- The profile contains no names or message authors. Keep it that way, and keep it encrypted. The repo is public.
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
