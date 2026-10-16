# Notes – the wiki data (states, powers, groups, issues) and the movement layer's build

Part of the 'hjerne' branch (2026-10-17). The owner's decision: concepts named in the news open a wiki page compiled
only from the amir's political answers – no analysis by Khabar. This part builds that data for every state, power,
group and issue the movement layer reads; the abstract concepts come from another part (docs/hjerne/begreber-ideer.json)
and are merged by the same build.

## 1. scripts/build_movement.py on this branch

- Paths: reads `.cache/movement/extract/*.json` and `synth/*.json` (local), `docs/hjerne/qa-index.json`; writes
  `public/viden/movement.json` and `public/viden/movement-index.json`. The `public/dev` copies are gone.
- The voice checks stay (`owned()`, `check()`). Khabar 2's `editor2.check_voice` and `knowledge.AGENT_WORDS/PROTECTED`
  are not on this branch, so their patterns are now in the script itself – verified identical to the khabar2 branch
  (pattern and flags). The check's protected names come from `docs/hjerne/knowledge-v0.json` when it is there, else only
  the script's own list of non-ruling persons and parties (so CI runs it too). The sentence rules (staged attacks,
  serving claims) moved into `serving_problems()`, which the wiki's check reuses.
- Measured: a rebuild with the committed 'built' time is **byte-identical** to the committed files (843,254 and
  188,203 bytes); `check()` finds nothing. 321 answers, 145 subjects, 1,036 readings, 122 current, 34 issues,
  267 expectations.
- `tests/test_movement.py` ports the khabar2 movement tests (minus the seed model and editor2 parts) and adds the
  owner's four newest-answer examples and a rebuild test (skipped without `.cache/movement`).

## 2. scripts/build_begreber.py → public/viden/begreber.json and begreber-index.json

The shared schema exactly (`version`, `built`, `items`; the index `version`, `items` with name, kind, aliases,
case_sensitive, n_answers). Run `py scripts/build_begreber.py` after build_movement.py, and again whenever
`docs/hjerne/begreber-ideer.json` changes (the test says so when the committed file is out of date).

**Pages (114):** 67 stat, 7 magt, 4 gruppe, 2 organisation, 34 sag.
- Every subject without `--` in `readings`/`current` (79) and Finland (only a relation names it). Names from
  knowledge-v0 (powers, then actors, then states), overridden where the model's name is a description:
  'Israel' (not 'Den israelske stat'), 'Yemen'; 13 subjects the model lacks have names in the script.
- Kinds: the seed's 7 powers are `magt` (EU too, as the model holds it); Hamas, Hizbollah, houthierne, RSF `gruppe`;
  NATO and Det Palæstinensiske Selvstyre `organisation` (the answers call it a self-rule without sovereignty, so not
  `stat`).
- `lead_da` = the layer's current reading (build_movement already lets the newest answer govern); without one the
  newest reading; Finland: its relation. Checked: Rusland 12/6/2026 (mellemniveau), Storbritannien 5/8/2026
  (Golfstaterne og Jordan), Iran 28/6/2026 (satellitstat), Saudi-Arabien 27/9/2026 (underordnet since 2015).
- `timeline` = the readings newest first (725 rows from 731: 6 repeats one answer gave twice through two syntheses
  merged at word similarity ≥ 0.5). 16 span readings named no day in their text ('Ifølge Hizb ut-Tahrirs svar
  samlede …'); they now carry their span from the row's own dates ('… svar fra 12/3/2016 til 29/7/2018 samlede …').
- `relations`: the 68 relation subjects on both parties' pages (136 rows): the current reading, else the newest.
- `answers`: tagged with the page in movement-index (states/powers/issues) or behind one of its readings/relations.
- **Issues** (`sag`): all 34 with a history. Ten issue ids are also state ids (egypten, indien, irak, iran, jordan,
  libanon, sudan, syrien, tyrkiet, yemen): those pages are `<id>-sagen` ('Iran-sagen'), linked first from the state's
  page. Lead = the history's opening sentence + its newest three (max 4 sentences); 'Den internationale tilstand'
  keeps sentences 1-4 instead (the default would drop China's reading). `lead_nr` = the newest answer the lead names by
  its day. Timeline = the notes of the answers the history rests on (438 rows).
- `related`: a sag links the pages it is named after, the pages its history names and the groups whose readings rest on
  its answers (most central first), then the issues above/below it in knowledge-v0. A state links its own issues, its
  relation partners, then the issues that link it; a small state no issue links gets the one or two issues its answers
  are tagged with most (Belarus → Ukraine og Rusland, Kosovo → Europa).
- `subject` = the page's key in movement.json: `readings`/`current` for stat/magt/gruppe/organisation, `issues` for a
  sag (Iran-sagen has subject 'iran' = the issue). Finland has none.

**Aliases (184)**, hand-written Danish forms (DR/TV 2/Ritzau usage): Saudi-Arabien/Saudiarabien, houthierne/
houthi-oprørerne/Ansar Allah (+ 'houthi', 'houthis': the machine's Danish writes 'Houthis' and 'Houthi-angreb'),
Storbritannien/Det Forenede Kongerige, Nato/NATO, Hviderusland, Jemen, issue forms like 'krigen i Ukraine',
'Iran-krigen', 'krigen i Sudan', 'Darfur', 'Golfstaterne', 'FN', 'ICC', 'Grønland', 'koranafbrændinger'. Ten pages
have none and are reached from other pages: six -sagen pages (all but Iran, Sudan, Syrien and Yemen, whose wars have
Danish names) and four issues where a state's name would do or the issue is an idea the concept pages may hold
(Afghanistan og Pakistan, Den intellektuelle kamp, Den internationale tilstand, USA og Europa).
- Rules (in the build and the test): no adjective or people-word (stoplist of 1,114 words incl. every nationality
  adjective/people form for the subjects; single words ending -isk/-sk/-lig or -aner/-enser/-itter/-iere/-mænd are
  refused, 'houthierne' reviewed as an exception); no ordinary Danish word; no alias on two pages (case-folded);
  case-sensitive pages have capitalised aliases. Deliberately **not** aliases: capitals and metonyms (Teheran, Moskva,
  Washington, Det Hvide Hus, Kreml – a link names the state, not a city), 'Saudi' (an English demonym), 'Selvstyret'
  (also Greenland's), 'Gaza'/'Vestbredden' (places; left for a future `sted` page), 'UK', 'England'.
- Link test against the live radar (618 items, Danish titles and summaries, whole word + possessive, longest first):
  Ukraine 105, USA 93, Israel 92, Rusland 76, Iran 71, EU 39, Europa 29, Saudi-Arabien 27, Yemen 20, Danmark 19 …;
  no wrong link seen in the examples ('Golfen' = the Gulf, 'Grønland-Danmark', 'pro-Palæstina-demonstration').

**The concept file** (`docs/hjerne/begreber-ideer.json`, not there when this was built): merged when present. A concept
that breaks the schema or a voice rule is left out; unknown answer numbers, relations and related ids are dropped; an
alias that breaks the alias rules is dropped; on an id clash the concept replaces the page, on an alias clash the
concept keeps the alias and the movement page loses it – each reported by the build. A page a concept names as related
links back to it. Invalid JSON (a file being written) is reported and skipped.

**Measured:** begreber.json 602,570 bytes (largest page USA, 63 KB), begreber-index.json 13,703 bytes; `check()` 0
problems. The 10 pages with most answers: USA 313, Storbritannien 191, Rusland 121, Den internationale tilstand 117,
EU 115, Frankrig 108, Kina 87, Saudi-Arabien 83, Tyrkiet 82, Iran 80. Twenty leads are older than 2020 because the
layer has nothing newer (Hamas 2017 – the layer says so itself –, NATO 2010, Polen 2018 …).

## 3. tests/test_begreber.py (15 tests)

The schema and the index exactly; every lead/timeline/relation text names Hizb ut-Tahrir and a time, with its
answer's date; every nr in movement-index.json; no alias on two pages; the stoplist (≥ 500) and the adjective/people
rules, with the refused forms named; the voice rules catch each case (den jødiske entitet, jøderne, agentstat, a staged
attack, a non-ruling party said to serve, a long quotation, a wrong date, an unknown answer); the newest answer governs;
every layer subject and issue has its page; relations on both pages; span dating and repeat merging; the concept merge
(id clash, alias clash, bad concept left out, back-links); the committed file equals a fresh build (skipped without
knowledge-v0.json); no local paths, long quotes or 'Claude' in the public files. Whole suite: 95 passed, 5 skipped
(cryptography/Pillow not installed locally).

## For the other parts

- **The app's linker:** match an alias as a whole word with an optional possessive (s, 's, ’s, '), longest alias first
  ('krigen i Ukraine' before 'Ukraine', 'Det Palæstinensiske Selvstyre' before nothing shorter), case per page.
  `n_answers` lets it skip thin pages; 'Danmark' links in many Danish stories to a page with one answer (Quran
  burnings) – consider not auto-linking it, or only once per story.
- A timeline row is `{date, nr, text_da}` and a relation `{with, text_da, date, nr}`: the answer's title and URL are in
  movement-index.json / movement.json by `nr`. The editor's new answers (answers.json on the digest branch, with
  `begreber` ids) are not merged at build time; the ids here are stable keys for them.
- **brain.py** matches the index's aliases instead of its FALLBACK_ALIASES once the index exists, so it loses the
  adjective stems and names ('amerikansk*', 'Trump', 'Teheran') the weighing used. The wiki must not link those; the
  brain may want both (index aliases + its fallback stems).
- **voice.py** `check_movement` flags 6 wiki texts the layer's own check passes: four read a government ('Styret under
  Hasina', 'BJP-regeringens' twice, 'regering under Hamdok'), which card H3 allows and build_movement neutralises with
  its GOVERNMENT pattern; one is a false hit on 'medieplatform' ('Frankrig via Tchad, Storbritannien som
  medieplatform' – states, no outlet is said to serve anyone); one is Japan 'ikke meget forskelligt fra vasaller' (a
  reading of a state). Giving voice.py's
  serving check the same GOVERNMENT pattern would make the two rule sets agree. (On the whole layer it flags nine.)
- Not committed by this part: `docs/hjerne/knowledge-v0.json` and `qa-index.json` (inputs, placed by the
  orchestrator) – the builds need them locally; the tests skip what needs them.
