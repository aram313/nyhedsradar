# Launched – 2026-10-17 11.03 Danish time

The owner said "Jeg må udgive og sætte kaldet op". Done the same day:

- **Code:** branch `hjerne` (with main merged in, 223 tests) pushed to main at 2008312; khabar.nu serves app v20261017t
  with Forside · Live · Analyser; the radar's first pass on the new code wrote `app.json`, `admitted.json` and
  `editor-gate.json` on the data branch.
- **The editor's routine** `trig_01B5p6DmEx8pz9cDLZzwxbHj` ("Khabar – redaktør (hver time, med hjernen)"): the new
  prompt of routine-prompt.md with the owner's private WEIGHING guide kept in the routine only; schedule
  `0 5-22 * * *` UTC = every hour 07-24 Danish summer time (06-23 in winter). Each run starts with `editor.py check`
  and stops in one line when nothing needs adjusting.
- **Not used:** the API trigger and the secrets `ROUTINE_FIRE_URL`/`ROUTINE_FIRE_TOKEN` (the fire endpoint was
  unverified). The gate step in radar.yml stays a dry run that only looks and logs; it can be wired later if the
  owner wants Claude called sooner than hourly.
- **First live run** (fired by hand at 11.10, 83 seconds): published a new lede, 30 informative headlines, level
  normal with two stories dropped, and a front page of 7 blocks (top, Danmark, Houthierne og Saudi-Arabien,
  Vestbredden og Gaza, udvikling, citat, live). The publish checks refused one judgement word ('aftalt spil') and a
  front-page story outside Live; the editor fixed both and published.
