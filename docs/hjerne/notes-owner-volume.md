# The owner's rule on how many stories Live shows (2026-10-17)

> "Mængderne af nyheder bestemmer redaktøren. Typisk vil vi gerne have de vigtigste på dagen, men nogle dage kan det
> vurderes, at der kommer rigtig mange gode nyheder, og derfor må vi tage flere ind."

**The rule:** the editor (Claude) decides how much goes into Live. On a normal day Live holds the day's most important
stories; on a day with many strong stories the editor takes in more; a quiet day is never padded.

**How (revised the same day, for speed and tokens):** the editor sets the day's **level**, and the radar applies it
continuously between the editor's runs, so a strong story appears at once and the editor's quarter-hour look stays
cheap. The editor can also take a single story in or out.

- The radar ranks every candidate by the brain (the books' order of importance, the amir's newest readings, the
  sources' fit). The level sets how far down the ranking Live reaches for the last 24 hours: `få` (only the sharpest –
  a quiet day), `normal` (the day's most important; the default), `mange` (a heavy day: more of the strong ones). The
  radar turns the level into a rank threshold and a soft count (e.g. about 25 / 45 / 80 stories in 24 hours – to be
  tuned on real data with scripts/rank_check.py), never cutting a big story or Danish politics on Islam, Muslims,
  integration and foreign policy.
- The editor's `take` adds a story under the line; `drop` removes one above it. Both last that Danish day.
- **Data (digest branch, written by `editor.py publish`):** `live.json` =

  ```json
  {"updated": "<iso>",
   "days": {"YYYY-MM-DD": {"level": "få" | "normal" | "mange",
                           "take": ["<story id>"], "drop": ["<story id>"],
                           "note": "<one line: why today's level>"}}}
  ```

  An id matches a story when it is the story's `id` or one of its `members` (clusters merge). Two days are kept.
- **The radar** reads live.json (from the digest branch) at each run and writes, besides the full candidate pool for
  the editor and search (data.json as today), a **slim `app.json`** with only what the app shows: the admitted stories
  of the last 48 hours (level + take − drop, plus every big story), with the fields the app needs. Fallback: no or a
  stale live.json (older than 2 hours between 06 and 24) → level `normal`.
- **The app** loads app.json (much smaller than today's 780 KB data.json) and shows it as Live and as the front page's
  pool; it falls back to data.json if app.json is missing. Search still covers every story (search.json).
- **The editor's input** shows the level and today's count, the candidates just above and just below the line, and the
  admitted stories that still need an informative headline (notes-owner-headlines.md); its update may set `level`,
  `take`, `drop`, `note`. The check says OPDATÉR when several admitted stories wait for their headline (say 8, or one
  waiting over 45 minutes between 06 and 24), besides its other reasons.
