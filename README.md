# Khabar (Nyhedsradar)

The app is called **Khabar** (خبر, "news"). The repository and folder keep the working name `nyhedsradar`.

A phone app (a full-screen web page added to the iPhone home screen) that watches about 60
news sources around the clock. It picks out the stories that matter to the WhatsApp group
*Debat/Nyheder Shabab* and sorts them into three sections: **Danmark**, **Mellemøsten** and
**Verden**, plus **Bevægelser**: where political movement is happening, as short attributed statements. The front page shows Claude's overview (07 and 22, a short summary of every article) on top and
then every story as it comes in, all sections mixed. Opening a story shows a short summary, how Danish, Western, Arab/Muslim
and Israeli media each tell it, and buttons to read, share (the phone's share sheet, so WhatsApp is one
tap away) or copy. Big stories and the most relevant news also trigger a notification.

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
   and headlines that name nothing. Each section shows its own top ~15 %; Danish stories must touch politics,
   Islam/Muslims or immigration. Busy Telegram channels show at most 6 lines a day.
6. **Self-learning, with no buttons:** posts from the community's own sources (marked
   `community` in `config/feeds.json`), big stories and what the user shares or opens are added to the
   profile and fade out over 30 days.
7. **Notifications:** at most one per story, batched, at least 20 minutes apart, at most
   15 per day, never between 23:00 and 07:00.
8. **Bevægelser:** the radar collects every line of Al Jazeera's Arabic urgent wire (and other one-line
   statements) in `lines.json`; at 07 and 22 Claude translates all wire lines of the period into Danish, groups
   them by topic in the group's own format and adds the edition on top of `moves.json` (earlier editions stay).
9. The result is written to `data.json` (the stories), `search.json` (everything read in the last two days,
   for the app's search) and `lines.json` on the `data` branch. The app (`public/`, published to GitHub Pages
   by `pages.yml`) reads those files and Claude's `digest.json` and `moves.json` from the `digest` branch.

## Secrets and settings (GitHub)

| Name | Kind | What |
|---|---|---|
| `PROFILE_KEY` | secret | Unlocks `config/profile.enc` (the encrypted group profile) |
| `VAPID_PRIVATE` | secret | Signs notifications |
| `PUSH_SUBS` | secret | JSON list of phone subscriptions (the code the app shows) |
| `VAPID_PUBLIC` | variable | Public half of the notification key, used by the app |
| `FEEDBACK_TOPIC` | variable | Private ntfy.sh topic that carries share/copy/open signals to the radar |

Local copies are kept in `.env` and `.secrets/`, both of which are gitignored.

## Commands

| Task | Command |
|---|---|
| Run the tests | `py -m pytest -q tests` |
| Preview the app locally | `py -m http.server 8765 --directory public` (needs a local `public/config.js` + `public/data.json`) |
| Rebuild the profile from a new chat export | `py scripts/build_profile.py <_chat.txt> .cache/profile.jsonl`, then encrypt (see CLAUDE.md) |
| Run the radar by hand in the cloud | `gh workflow run radar.yml` |
| See what each section would show with the current settings | `py scripts/rank_check.py` |

## Stack

Python 3.12 (standard library + numpy, fastembed, pywebpush), GitHub Actions, GitHub Pages,
plain HTML/CSS/JS progressive web app.
