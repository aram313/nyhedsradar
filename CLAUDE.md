# CLAUDE.md — Nyhedsradar

Project-specific instructions. The workspace-wide rules are in `E:\CLAUDE.md` and
`E:\STRUCTURE.md` and apply here too — this file only adds what is specific to this
project.

## What this project is

Telefon-app der automatisk finder nyheder, der passer til Debat/Nyheder Shabab-gruppen, med kopiér-knap og notifikationer

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
- `src/radar/run.py` is one radar run: dedupe → embed → self-learn → score → cluster → notify → write state.
- `src/radar/push.py` sends Web Push; `src/radar/feedback.py` reads copy taps from the ntfy.sh relay.
- `public/` is the PWA. `config.js` and `data.json` there are local-preview only (gitignored);
  `pages.yml` generates the real `config.js`.
- State lives on the force-pushed orphan branch `data` (no history), read back at the start of each run.
- `config/profile.enc` = output of `scripts/build_profile.py`, AES-256-CBC/PBKDF2 (200k iterations) with `PROFILE_KEY`:
  `openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in .cache/profile.jsonl -out config/profile.enc -pass env:PROFILE_KEY`

<!-- How the pieces fit together. Where the entry point is. What depends on what.
     Update this when the shape of the project changes. -->

## Scheduling and Claude routines

- GitHub's own `*/5` schedule is unreliable (it ran once in a whole night). The real clock is an external
  scheduler (Upstash QStash or cron-job.org, set up by the owner) calling the workflow_dispatch API with a
  fine-grained token limited to Actions on this repo. GitHub's schedule stays as a fallback.
- **Temporary clock (2026-10-10):** Windows Task Scheduler task `Nabd vaekkeur` runs `scripts/pc-clock.vbs` every
  5 minutes while the PC is on (uses the PC's own `gh` login; logs to `.cache/pc-clock.log`). Remove it with
  `Unregister-ScheduledTask -TaskName 'Nabd vaekkeur' -Confirm:$false` once `scripts/setup-clock.ps1` (QStash) has
  been run by the owner. Note: `gh` logins made from Claude's sandboxed Bash are not visible to Windows tasks.
- Claude Code cloud routines on the owner's subscription (claude.ai/code/routines):
  - `trig_01B5p6DmEx8pz9cDLZzwxbHj` editor: fires 05,06,15,16 UTC, works only at 07/17 Danish time,
    writes `digest.json` to the orphan `digest` branch.
  - `trig_01A5Nc5cQACxsN2mpYAqymwE` caretaker: daily 04:30 UTC, repairs/disables feeds in config/feeds.json,
    appends a line to docs/radar-status.md.
- Phones: `PUSH_SUBS` secret = JSON list of Web Push subscriptions from the app's 'NYHEDSRADAR-PUSH:' code.
  Test with `gh workflow run push-test.yml`.

## Project-specific conventions

- The owner wants it **fully automatic**: no feedback buttons. Adaptation comes from community
  sources, big stories and silent copy taps only.
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
