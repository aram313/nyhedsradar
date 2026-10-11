# CLAUDE.md — Nyhedsradar

Project-specific instructions. The workspace-wide rules are in `E:\CLAUDE.md` and
`E:\STRUCTURE.md` and apply here too — this file only adds what is specific to this
project.

## What this project is

Telefon-app (Khabar) der automatisk finder nyheder til Debat/Nyheder Shabab-gruppen, delt i Danmark, Mellemøsten og Verden, med deling til WhatsApp og notifikationer

<!-- Expand: the purpose, the users, the constraints that are not obvious from the
     code. This is the context you would want if you were picking this up cold. -->

## Stack

- **Type:** `web-app`
- **Technologies:** python, github-actions, pwa

## Commands

<!-- Fill these in as soon as they exist. Exact, copy-pasteable, no placeholders. -->

| Task | Command |
|---|---|
| Install dependencies | Cloud only: `pip install -r requirements.txt` (runs in Actions; locally only numpy + pytest are needed) |
| Run in development | `py -m http.server 8765 --directory public` |
| Run tests | `py -m pytest -q tests` |
| Build for production | Push to `main`; `pages.yml` publishes `public/` |
| Run the radar now | `gh workflow run radar.yml` |

## Architecture

- `src/radar/feeds.py` fetches and parses every source type (rss, gnews, telegram, youtube). Stdlib only.
- `src/radar/run.py` is one radar run: dedupe → embed → self-learn → score → cluster (+ second look at cards)
  → sections and rank → show/important/big → translate → notify → write state, `data.json` and `search.json`.
- `src/radar/sections.py` places stories in dk / me / world and gives the word signals (core, core_dk, trivia,
  local, named) used by the rank; the word lists live in `config/sections.json` (format explained in its `_help`).
  Every source in `config/feeds.json` has a media `group` (dk, west, mena, il, channel) and some a section hint `sec`;
  `label` is the readable name the app shows, `official` marks a news outlet's own Telegram channel (not an
  unverified channel) and `wire` a one-line statement feed (Al Jazeera urgent: counts as an outlet, feeds
  `lines.json` and the Bevægelser briefing, never a card of its own).
- `src/radar/thumbs.py` gives every card a small picture (feed image → another outlet's → the og:image of the lead's
  article page, then of up to four other outlets' pages; a story without one shows its outlet's initials in the app –
  the owner likes those tiles and declined pictures found by the editor, 2026-10-11),
  shrunk with Pillow to a 144 px JPEG in `state/t/` (served from the data branch); unverified Telegram channels
  never lend one. `state/pics.json` remembers page images and failed pictures for 3 days.
- `src/radar/push.py` sends Web Push; `src/radar/feedback.py` reads copy taps from the ntfy.sh relay.
- `src/radar/stats.py` keeps the owner's statistics (2026-10-11): the app posts `visit` (home screen or browser, iPhone/Android/other, time zone, language, how it came; `first` on 'Kom i gang') and `leave` (seconds, tabs, stories opened) to the relay; read/share signals give the most read stories (the owner's own carry `me` and are not counted). Counts per Danish day in `state/stats.enc`, AES-GCM with a key from ADMIN_KEY (sha256('khabar-stats|' + code)); the app decrypts it in the admin-only block at the top of Indstillinger. Nothing is stored on phones and no id follows a person – the owner declined anonymous ids for unique visitors (2026-10-11: consent rules) and wants no consent prompt or button, so place in Denmark is not collected (it would need a permission prompt or an IP lookup); country comes from the time zone.
- `scripts/editor.py` is the Claude editor's tool (input / publish, see its docstring). It keeps one overview per
  Danish date: each update adds short 'Who: what' lines to the day's topics (newest first); the day lists every
  wire line id its updates were given (`ids`), so the next update gets only new ones. Old edition archives
  (`briefs`) are folded into days automatically.
- `public/` is the PWA. `config.js` and `data.json` there are local-preview only (gitignored);
  `pages.yml` generates the real `config.js`.
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
  - `trig_01B5p6DmEx8pz9cDLZzwxbHj` editor: fires twelve times a day (since 2026-10-11, the owner's choice, ~1/10 of his plan):
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
    (30 days) and `summaries.json` (summaries in `items`, checked headlines in `titles`; 4 days) on the orphan `digest` branch. Only the first update at or after 21 Danish time notifies the phones.
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
- The UX review (2026-10-11, owner chose it): five tabs (Forside, Danmark, Mellemøsten, Verden, Live – keep Mellemøsten and
  Verden apart: the group's core is the Middle East and together they are 100+ stories a day). The front page, organised by
  story and time: date + the editor's lede (no 'nye siden' chip), 'Dagens historie' (the recap's lead topic matched to a top
  story by shared words: hero, timeline, a quote from it; no 'Sådan dækkes det' – coverage lives in the opened story), 4 more
  top stories (never the main story again), 'Følg udviklingen' (the 3 developments that moved last, not the main story's),
  'Dagens citat' if the package had none, 'Live' (the 3 newest Live stories). No section glance, no recap on the front page:
  the Udvikling page (not a tab; reached from the front page, the stories and search, left by a tab or the logo with a back
  mark) holds the editor's lines once (2026-10-11 the owner had the recap and the developments merged – as two views
  they clashed): 'I dag' with the day's line count, update time and 'Del resumé' (the WhatsApp text); the day's topics in
  the editor's order, each a card with its lines of the day, newest first, that unfolds into the whole development across
  the days ('Hele forløbet'); then 'Fulgt de seneste dage' (developments the day has not touched); then 'Tidligere dage'
  (whole recaps, to read or share). A development tapped elsewhere opens unfolded; the recap notification (?digest=1)
  opens the page at the top. The name is 'Live' everywhere. Foreign headlines show in Danish by default (the editor's
  checked Danish first, else the machine's; the opened story names the original). The intro plays on the first visit and
  after six hours away, else the app opens straight in. Text size follows the phone (iPhone Dynamic Type) or the setting
  (every font size is `calc(Npx * var(--ts, 1))`, --ts set on #list). Old news: only the box on the page, the top bar stays
  quiet. Shared texts end with 'via khabar.nu'. Bump `?v=` on every change: the service worker serves versioned files from
  its cache. Colour is minimal (the owner found section-coloured labels
  'in your face'): a small section dot on mixed lists, red only for big stories and 'live'. Headlines guide the eye
  with bold keywords (who and where) instead. Block titles and day markers must never look alike.
- The app never mentions Claude in visible text and has no 'how Khabar chooses' explainer (owner's request,
  2026-10-10). Default look: Dæmpet (light) and Notion (dark); the 'Blød' tone was removed.
- Danish politics must never be buried: keep the Danish lift (`rank_core_dk`) and the dk-section rules when
  tuning the rank. Before changing thresholds or word lists, run `py scripts/rank_check.py` (one radar pass on a
  copy of the live state, no fetching or embedding) and compare what each section would show.
- The profile contains no names or message authors. Keep it that way, and keep it encrypted. The repo is public.
- Facebook, Instagram, TikTok and X cannot be followed. Do not add scrapers for them without the owner's explicit decision (cost/ToS risk).
- Tests use `tests/fake_embed.py` instead of the real model, so they run offline without fastembed.

<!-- Anything that differs from, or adds to, the workspace standard. If nothing
     differs, say so explicitly so the next session does not go looking. -->

## Constraints and gotchas

<!-- Things that will bite someone who does not know them. External services that
     must be running, ports in use, data that must be seeded first, known-fragile
     areas. Add to this list every time you hit one. -->

## Definition of done

A change is finished when:

1. Tests pass.
2. `CHANGELOG.md` has an entry under `## [Unreleased]`.
3. `.project.json` has an updated `updated` date.
4. `README.md` still describes reality.
5. The work is committed with a Conventional Commit message.
6. The owner has been told what changed, in plain language.
