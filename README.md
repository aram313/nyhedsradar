# Khabar (Nyhedsradar)

The app is called **Khabar** (خبر, "news"). The repository and folder keep the working name `nyhedsradar`.

A phone app (a full-screen web page added to the iPhone home screen) that watches about 120
news sources around the clock. It picks out the stories that matter to the WhatsApp group
*Debat/Nyheder Shabab* – weighed by the order of importance of Hizb ut-Tahrir's political books and the amir's newest
answers, used only to choose and order the news; the app itself shows no analysis – and marks each with its section
(**Danmark**, **Mellemøsten**, **Verden**). Every story carries an **informative headline** the editor writes – who
did or said what, where – instead of the outlets' own, which often only make the reader curious (until the editor has
written one: the outlet's headline in Danish, or for a plain teaser its first sentence; the original is in the opened
story). Names of people, parties and places are in bold. Three tabs:

- **Forside** – the front page the editor composes at each update by its own taste and the brain: the day in one
  sentence, **Dagens historie** (the main story with its picture, how it developed through the day, and the amir's
  answer on its subject when there is one), titled groups of stories, **Følg udviklingen**, the day's quote, an answer
  of the amir's, the newest Live stories, a line of fact – in the order the editor chose (a fixed front page when there
  is no fresh composition).
- **Live** – the stories of the day as the editor weighs them – fewer on a quiet day, more on a heavy one – the newest or
  the most important first.
- **Analyser** – Hizb ut-Tahrir's answers to political questions, the newest first (321 from 2004 to 2026 and every new
  one), with a search field and the reader: the question, the answer in short, what it reads, the original.

Concepts named in the news (states, powers, groups, issues, agreements, places, ideas) open a **wiki page** compiled only
from those answers – each block labelled as Hizb ut-Tahrir's answer with its date, the newest answer governing – with its readings through the years and today's
stories that name it. The **Udvikling** page holds every development step by step, the recap of the day (the day's most
important movements as short 'Who: what' lines in the style of Al Jazeera's breaking wire, grouped by topic, updated
through the day) and the earlier days. Every story has a small picture; opening it shows a short summary, how Danish,
Western, Arab/Muslim, Israeli and other media each tell it, and buttons to read, share (the phone's share sheet, so
WhatsApp is one tap away) or copy. Top stories and the most relevant news also trigger a notification; a phone signs up
with one tap (no code to send).

## Status

**active** · Created 2026-10-09 · Type: `web-app`

## How it works

1. **Every 5 minutes** (often 10–20 in practice) a GitHub Actions job (`.github/workflows/radar.yml`)
   fetches every source in `config/feeds.json`: RSS feeds, Google News searches for sites without
   a feed, public Telegram channels and YouTube channels.
2. Each new headline is turned into a meaning vector by a small multilingual language model
   (Danish, English, Arabic, Turkish). It is then compared with the **profile**: about 6,500 links
   the group has shared, plus what the radar has taught itself (see below).
3. **Duplicates:** the same link or headline is only ever seen once. Articles about the same
   story from several outlets become one card; a second look joins cards whose headlines say the same
   thing in different languages. When 4 or more outlets cover a relevant story, it becomes a **big story**;
   a political story most Danish outlets carry is a big story in Denmark.
4. **Sections** (`src/radar/sections.py`, words in `config/sections.json`): places, parties and people in
   the headline decide Danmark / Mellemøsten / Verden; stories without telling words follow the most similar
   placed stories, their language and their source (`sec` hints and media `group` in `config/feeds.json`).
5. **Rank** = the group's taste (percentile within the language) + up to 20 for the number of established
   outlets + a lift for core subjects (Danish politics, Islam and Muslims, immigration get the biggest, because
   the group's own links are mostly about other countries) − light news (weather, sport, royals), everyday crime
   and headlines that name nothing – **plus the brain** (`src/radar/method.py`, `config/method.json`): each story's
   tier in the books' order of importance (the leading state's acts with another power first, then its own acts, a
   great power's acts, who controls a state, the major issues, the campaign against Islam and its concepts …; the powers
   as the amir's newest answers read them) lifts or lowers it, and the sharpest tiers reach the editor even below the
   taste bar. Each section shows its own top ~15 %; Danish stories must touch politics, Islam/Muslims or immigration.
   Busy Telegram channels show at most 6 lines a day. Sources carry their camp (whose view they give); sources added
   for their camp never move the established sources' scale.
6. **Self-learning, with no buttons:** posts from the community's own sources (marked
   `community` in `config/feeds.json`), big stories and what the user shares or opens are added to the
   profile and fade out over 30 days.
7. **Live's level** (`src/radar/level.py`): the editor sets the day's level – `få`, `normal` or `mange` – and may take
   a story in or drop one (`live.json` on the digest branch). The radar turns the level into a rank floor and a soft
   count for the last 24 hours, never cuts a big story or Danish politics on Islam, Muslims, integration and foreign
   policy, keeps a story it showed while its rank stays near the line, and writes `app.json` – the stories the app
   shows, with only the fields it reads (about a sixth of `data.json`). Which outlet leads a story follows the sources'
   measured fit (`fit` in `config/feeds.json`): the most informative headline leads; per-source `drop`/`cut` rules clean
   the headlines at intake (blogs, opinion pieces, betting ads, site names).
8. **Notifications:** at most one per story Live shows, batched, at least 20 minutes apart, at most
   15 per day, never between 23:00 and 07:00.
9. **Pictures:** each card gets a small square picture – its own feed image, another outlet's picture of the
   same story, or the article page's share image – shrunk to a few kilobytes (`src/radar/thumbs.py`, files in
   `t/` on the data branch). Telegram channels never lend a picture.
10. **The editor:** the radar collects every line of Al Jazeera's Arabic urgent wire (and other one-line statements)
   in `lines.json`. After every radar pass the quarter-hour look (`scripts/editor.py gate`, plain Python: has anything
   of weight happened since the last update?) fires the editor's Claude routine when something has – once per reason,
   at most `editor_fires_per_day` a day within the subscription's run cap (docs/hjerne/cadence.md). The routine runs
   `scripts/editor.py check` and, when the reason holds, `scripts/editor.py input` (the brain – the books'
   order of weight and each power's current reading –, the front page now, the day so far, the stories and wire lines
   since the last update, the stories in Live without its headline, Live's level and line, the front page's
   composition), writes a small update – the lede, the picks, short summaries, an informative headline for every story
   still without one, the day's level, the front page's blocks and the most important new movements as 'Who: what'
   lines under the day's topics, all of it reality only – and runs `scripts/editor.py publish`, which checks it
   (`scripts/voice.py`: the content rules and no curiosity headline), fills in links, sources and times and writes
   `digest.json` (the day), `moves.json` (the last 30 days), `summaries.json` (summaries and headlines), `live.json`
   (the level), `front.json` (the composition) and, for a new answer of the amir's, `answers.json` to the digest
   branch. The look also calls the editor when stories wait for their headline (8 of them, or one for 45 minutes).
11. The result is written to `data.json` (every candidate, for the editor), `app.json` (what the app shows), `search.json` (everything read in the last two days,
   for the app's search), `lines.json` and `analyses.json` (the text of the amir's newest answers) on the `data`
   branch. The app (`public/`, published to GitHub Pages by `pages.yml`) reads those files and the editor's files from
   the `digest` branch; the movement layer and the wiki (`public/viden/`, built by `scripts/build_movement.py` and
   `scripts/build_begreber.py`) are published with it.
12. **Energy prices** (`src/radar/energy.py`, page `public/energi/` = khabar.nu/energi): after each radar pass
   the job fetches Brent, WTI, RBOB, ULSD, TTF and Henry Hub futures and USD/DKK (Yahoo Finance), the Brent and
   WTI forward curves, EIA's physical spot prices (via FRED), every Circle K/INGO and Q8/F24 station's pump
   price, and computes crack spreads, physical-minus-paper Brent and prices in kroner per litre. The result is
   `energy.json` on the data branch, with the energy stories of the last three days from `data.json` and
   `lines.json`. Each source has its own clock and a failed fetch keeps the last good numbers.

## Secrets and settings (GitHub)

| Name | Kind | What |
|---|---|---|
| `PROFILE_KEY` | secret | Unlocks `config/profile.enc` (the encrypted group profile) |
| `VAPID_PRIVATE` | secret | Signs notifications |
| `PUSH_SUBS` | secret | JSON list of phone subscriptions (the code the app shows) |
| `VAPID_PUBLIC` | variable | Public half of the notification key, used by the app |
| `FEEDBACK_TOPIC` | variable | Private ntfy.sh topic that carries share/copy/open signals to the radar |
| `ROUTINE_FIRE_URL` | secret | The editor routine's API trigger (claude.ai/code/routines); without it the look is a dry run |
| `ROUTINE_FIRE_TOKEN` | secret | The token of that trigger |

Local copies are kept in `.env` and `.secrets/`, both of which are gitignored.

## Commands

| Task | Command |
|---|---|
| Run the tests | `py -m pytest -q tests` |
| Preview the app locally | `py -m http.server 8765 --directory public` (needs a local `public/config.js` pointing at copies in `public/dev/`) |
| Rebuild the wiki after a change to the concept pages | `py scripts/build_begreber.py` |
| See what the editor's quarter-hour look sees | `py scripts/editor.py check` |
| Rebuild the profile from a new chat export | `py scripts/build_profile.py <_chat.txt> .cache/profile.jsonl`, then encrypt (see CLAUDE.md) |
| Run the radar by hand in the cloud | `gh workflow run radar.yml` |
| See what each section would show with the current settings | `py scripts/rank_check.py` |
| See what the editor would get / check an edition without publishing | `py scripts/editor.py input` · `py scripts/editor.py publish <file>` |

## Stack

Python 3.12 (standard library + numpy, fastembed, pywebpush), GitHub Actions, GitHub Pages,
plain HTML/CSS/JS progressive web app.
