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

## Still to do in the live routine (2026-10-17, after launch): no 'Ifølge …' in a new answer

The app now labels every block of Hizb ut-Tahrir's text itself ('Hizb ut-Tahrirs svar · d/m/åååå'), and `editor.py
publish` refuses a new answer whose note or readings say 'Ifølge Hizb ut-Tahrirs svar …' or 'Ifølge svaret …'. The
prompt in the editor's routine `trig_01B5p6DmEx8pz9cDLZzwxbHj` still asks for that opening, so until it is changed an
update that notes a new answer is refused once and must be rewritten (the refusal says how). Change two places in the
routine's prompt (docs/hjerne/routine-prompt.md holds the new text):

1. In the opening paragraph, replace
   > Hizb ut-Tahrir's answers appear only as the movement's own, attributed ("Ifølge Hizb ut-Tahrirs svar af d/m/åååå …"), and only in the "answer" object below.

   with
   > Hizb ut-Tahrir's answers appear only as the movement's own, and only in the "answer" object below: the app shows them under their own label ("Hizb ut-Tahrirs svar · d/m/åååå"), so you write them in plain Danish without "Ifølge …".

2. In step 4, the `answer` bullet: replace
   > a note of 2-4 sentences and one reading per subject it reads, each beginning "Ifølge Hizb ut-Tahrirs svar af d/m/åååå …".

   with
   > a note of 2-4 sentences and one reading per subject it reads, each saying what the answer reads in plain Danish without "Ifølge Hizb ut-Tahrirs svar …" or "Ifølge svaret …" ("Saudi-Arabien er underordnet USA"; the app labels them "Hizb ut-Tahrirs svar · d/m/åååå") – still the answer's reading as it says it, never your own.
