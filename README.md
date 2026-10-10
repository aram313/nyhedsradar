# Khabar (Nyhedsradar)

The app is called **Khabar** (خبر, "news"). The repository and folder keep the working name `nyhedsradar`.

A phone app (a full-screen web page added to the iPhone home screen) that watches about 50
news sources around the clock. It picks out the stories that match what the WhatsApp group
*Debat/Nyheder Shabab* usually shares, and gives each one a copy button that puts the
headline and link on the clipboard, ready for WhatsApp. Big stories and the most relevant
news also trigger a notification.

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
   story from several outlets become one card ("Også hos 4 andre kilder"). When 4 or more
   outlets cover a relevant story, it becomes a **big story**.
4. **Self-learning, with no buttons:** posts from the community's own sources (marked
   `community` in `config/feeds.json`), big stories and the user's copy taps are added to the
   profile and fade out over 30 days.
5. **Notifications:** at most one per story, batched, at least 20 minutes apart, at most
   15 per day, never between 23:00 and 07:00.
6. The result is written to `data.json` on the `data` branch. The app (`public/`, published
   to GitHub Pages by `pages.yml`) reads that file.

## Secrets and settings (GitHub)

| Name | Kind | What |
|---|---|---|
| `PROFILE_KEY` | secret | Unlocks `config/profile.enc` (the encrypted group profile) |
| `VAPID_PRIVATE` | secret | Signs notifications |
| `PUSH_SUBS` | secret | JSON list of phone subscriptions (the code the app shows) |
| `VAPID_PUBLIC` | variable | Public half of the notification key, used by the app |
| `FEEDBACK_TOPIC` | variable | Private ntfy.sh topic that carries copy taps to the radar |

Local copies are kept in `.env` and `.secrets/`, both of which are gitignored.

## Commands

| Task | Command |
|---|---|
| Run the tests | `py -m pytest -q tests` |
| Preview the app locally | `py -m http.server 8765 --directory public` (needs a local `public/config.js` + `public/data.json`) |
| Rebuild the profile from a new chat export | `py scripts/build_profile.py <_chat.txt> .cache/profile.jsonl`, then encrypt (see CLAUDE.md) |
| Run the radar by hand in the cloud | `gh workflow run radar.yml` |

## Stack

Python 3.12 (standard library + numpy, fastembed, pywebpush), GitHub Actions, GitHub Pages,
plain HTML/CSS/JS progressive web app.
