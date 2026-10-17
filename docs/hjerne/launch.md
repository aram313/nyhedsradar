# Launch of the hjerne branch – the deploy chat's checklist

Branch `hjerne` holds rounds 1 and 2 of the brain (the owner's decisions of 2026-10-17): the three tabs Forside · Live ·
Analyser, the wiki, the amir's answers, the brain in the radar's rank, the editor's informative headlines, its level for
Live (live.json → app.json), its composed front page (front.json), the sources' fit and filters, the speed work, and the
quarter-hour look that fires the editor's routine. Nothing of it is pushed yet. Do the steps in this order: the code
first, then the secrets, then the routine – the new routine prompt needs the new `scripts/editor.py`.

## 1. Before the merge

1. In the hjerne worktree: `git status` is clean and `py -m pytest -q tests` passes (222 passed, 5 skipped on
   2026-10-17), `node --check public/app.js` and `node --check public/sw.js` are clean.
2. `git fetch origin` and look at what main got since the branch point:
   `git log --stat hjerne..origin/main`.
   On 2026-10-17 10.45 that was one commit: `docs/radar-status.md` (the caretaker's daily line). Other chats work on
   main too; expect:
   - **the caretaker routine** (`trig_01A5Nc5cQACxsN2mpYAqymwE`, daily 04.30 UTC): `docs/radar-status.md` and repairs or
     disabled sources in **`config/feeds.json`** – hjerne changed that file heavily (camps, `fit`, `drop`/`cut`, 36 new
     sources, six removed). On a conflict keep hjerne's file and apply the caretaker's change by hand (a URL fixed, a
     source `"disabled": true`).
   - **the energy chat**: `src/radar/energy.py`, `public/energi/`, the energy step in `.github/workflows/radar.yml`,
     `energyUrl` in `.github/workflows/pages.yml`. Take main's version of those; hjerne never changed them (its radar.yml
     and pages.yml changes are the digest fetch of live.json, the editor's look step, `appUrl` and `frontUrl`).

## 2. Merge and deploy

1. In the main checkout: `git checkout main && git pull` then `git merge --no-ff hjerne` (message e.g.
   `feat: the brain – Forside · Live · Analyser, the editor's headlines, level and front page`).
2. Resolve conflicts as above, then `py -m pytest -q tests` again on main.
3. `git push origin main`. `pages.yml` publishes the app with the new `config.js` (appUrl, frontUrl). Until the radar's
   next pass writes `app.json` the app reads `data.json` (and keeps only what the radar marked `live` once it has).
4. Start one radar pass (`gh workflow run radar.yml`) and check on the `data` branch that `app.json` and
   `admitted.json` exist, and in the run's log that "Editor's quarter-hour look" ends in
   `Gate: not fired – … (dry run (no --fire))` or `Gate: no fire – …` (no secrets yet: it only looks).

## 3. The GitHub secrets

1. At claude.ai/code/routines open the editor routine `trig_01B5p6DmEx8pz9cDLZzwxbHj` and add an **API trigger**.
   It shows a URL and a token.
2. In the repository: Settings → Secrets and variables → Actions → New repository secret:
   - `ROUTINE_FIRE_URL` = the trigger's URL,
   - `ROUTINE_FIRE_TOKEN` = its token.
   Never paste either into a file, a commit or a chat.
3. The next radar pass fires the routine when the look says OPDATÉR (the log: `Gate: fired – … (HTTP 200)`); every fire
   is kept in `editor-gate.json` on the data branch.

## 4. The routine itself

1. **Copy the owner's private WEIGHING guide out of the routine's current prompt first.** It lives only there and is
   never committed (the repo is public).
2. Replace the prompt with the text of `docs/hjerne/routine-prompt.md` below its `---` line, and put the WEIGHING guide
   back on the line `[WEIGHING-GUIDE]`.
3. **Remove the routine's schedule** (the twelve fixed times: 06, 09, 12, 14-22 UTC). From now on only the API trigger
   starts it. Keep its repository and branch as they are (it reads main's `scripts/editor.py` and pushes only the
   `digest` branch).
4. `editor_fires_per_day` in `config/settings.json` is **12**. Read the account's daily routine run cap at
   claude.ai/code/routines (or `/usage`); the caretaker takes one run a day, and leave one or two for the owner. If the
   cap allows more, raise the number on main (the gate reads it at every look): headlines come faster – with 12 a story
   waits up to about two hours for its headline and none comes after the day's last fire (often 21-22); a quarter of an
   hour would need 40-70 fires (docs/hjerne/cadence.md). About 535,000 tokens a day at 12 (about 1.2 of the old twelve
   updates).

## 5. The first live day – what to watch

- **The fires.** radar.yml's look step every pass: `Gate: fired` at most `editor_fires_per_day` a Danish day, the
  first after 06, none at night unless a big story; no `HTTP 429` (the cap). The routine's runs at claude.ai/code/routines.
- **The first updates are large.** The first input lists up to 30 stories without the editor's headline, and the first
  publish removes the round-1 headlines that break today's rules (44 of 374 in the 17/10 file: questions, 'Analyse: …',
  '– video', 'Besættelsesstyrker …' without Israel's name), which come back to be written. Expect two or three updates
  before every story in Live has its headline; `editor.py check` says how many wait.
- **Live's size.** `py scripts/editor.py check` (or data.json's top-level `live`): today's level, the count in 24 hours
  and the radar's line. Measured on 15-17/10: få 30-40, normal 43-56, mange 75-86 stories. If the editor's level shows
  `forældet` in the daytime, the editor has not published for six hours.
- **The front page.** `front.json` on the digest branch, the check's `Composition (…)` line, and the app drawing it in
  the editor's order; without a composition from the last six hours the app shows the fixed page.
- **Headlines.** Spot-check a dozen: informative, no question or teaser, Israel named ('israelske styrker'), no
  judgement of Khabar's own, the same news as the article 'Læs' opens.
- **Danish politics never buried**: Danish stories on Islam, Muslims, integration and foreign policy in Live and high on
  the front page.
- **The owner's iPhone**: pull to refresh and a background reload while reading Live (nothing jumps); a big story that
  changes its lead outlet while opened (it stays open and does not glow); text size large (three headline lines); the
  intro.

## 6. If something goes wrong

- The routine fires too often or wrongly: delete the secret `ROUTINE_FIRE_TOKEN` (the look goes back to a dry run) or
  set `editor_fires_per_day` to 0; give the routine its schedule back if the old rhythm is wanted meanwhile.
- The app: revert the merge commit on main (`git revert -m 1 <merge>`); the data and digest branches need nothing –
  the old app ignores app.json, live.json and front.json.
- Live too small or too large: the editor's level is the lever; the floors and counts are `live_levels` in
  config/settings.json (tune with `RANK_CHECK_LEVEL=få|normal|mange py scripts/rank_check.py` on a copy of the state).
