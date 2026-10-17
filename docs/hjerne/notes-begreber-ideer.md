# Notes – the wiki data: the political concepts (begreber-ideer.json)

Part of the 'hjerne' branch (2026-10-17). The owner's decision: a concept named in the news opens a wiki page compiled
only from the amir's political answers – no analysis by Khabar. The states, powers, groups and issues come from the
movement layer (scripts/build_begreber.py, see notes-begreber.md); this part writes the abstract concepts, agreements,
places, organisations and processes in the same schema: `docs/hjerne/begreber-ideer.json`, `{"items": {id: page}}`.
`scripts/build_begreber.py` merges it into `public/viden/begreber.json` and the linker's `begreber-index.json`.

## 1. What is in the file

**90 pages** (begreb 33, sted 19, aftale 16, organisation 15, proces 7):

- begreb – the method's categories: foerende-stat, stormagt, mellemmagt, regional-magt, satellitstat, underordnet-stat,
  uafhaengig-stat, verdensordenen, plan-og-fremgangsmaade; the powers' doctrines and tools: kolonialisme, den-dybe-stat,
  usas-nationale-sikkerhedsstrategi, monroe-doktrinen, america-first, fred-gennem-styrke, krigen-mod-terror,
  sanktioner, missilskjold, petrodollaren, dollarens-dominans, sikkerhedskoordinering, regionalt-nato, militaerkup,
  foederalisme; the ideas: moderat-islam, demokrati, sekularisme, nationalisme, kapitalisme, menneskerettigheder,
  folkeretten, khilafah, tostatsloesningen
- aftale: abraham-aftalerne, makkah-pagten, camp-david-aftalen, oslo-aftalerne, aarhundredets-aftale,
  sykes-picot-aftalen, balfour-erklaeringen, lausanne-traktaten, minsk-aftalerne, atomaftalen, stockholm-aftalen,
  annan-planen, doha-aftalen, inf-traktaten, aukus, bretton-woods
- sted: hormuzstraedet, bab-el-mandeb, det-roede-hav, suezkanalen, sortehavet, det-oestlige-middelhav,
  det-sydkinesiske-hav, golanhoejderne, vestbredden, gaza, jerusalem, krim, donbas, idlib, karabakh, darfur,
  balochistan, oestturkestan, vestsahara
- organisation: nato, fn, fns-sikkerhedsraad, imf, g20, opec, den-arabiske-liga, den-afrikanske-union, ecowas,
  den-internationale-straffedomstol, sco, brics, kvartetten-sudan, quad, commonwealth
- proces: normalisering, blokaden-af-iran, brexit, astana-processen, geneve-processen, det-arabiske-foraar, baelte-og-vej

**Fields**, as the shared schema has them:

- `lead_da` – at most four sentences, every one naming Hizb ut-Tahrir ('Ifølge Hizb ut-Tahrirs svar af d/m/åååå …',
  'Hizb ut-Tahrirs svar af … læser …'). The newest answer governs: every lead names the page's newest answer by its
  day. Where that answer is the substance, the lead opens with it (NATO, tostatsløsningen, Idlib, Vestsahara,
  kapitalisme, missilskjoldet, FN's Sikkerhedsråd, Minsk-aftalerne, Bælte og Vej); where it only touches the page,
  an explanatory sentence opens and the newest follows (Verdensordenen, Abraham-aftalerne, Sykes-Picot …).
- `lead_nr`/`lead_date` – the page's newest answer, which the lead names (the issue pages' convention), so the brain
  dates a concept's reading by its newest answer: 39 leads are of 2026, 21 of 2025; the oldest is Den Arabiske Liga
  (20/5/2013, the newest answer that reads it).
- `timeline` – one row per answer, newest first, each row opening with its own answer's day.
- `answers` – the timeline's and the lead's answers plus answers that mention the concept without a row of their own;
  newest first by (date, nr), as the merge sorts them.
- `related` – the concepts it names first, then the page of the issue it belongs to (e.g. Vestsahara → nordafrika,
  Astana-processen → syrien-sagen), then states and powers by their layer ids. Every id is a page of the merged wiki.
- `relations` – empty: the relations between two subjects are the layer's.
- `subject` – only on `nato`, the one page that is the layer's own key. A concept that merely belongs to a subject or
  an issue links that page in `related` instead (notes-begreber.md: 'subject' is the page's id in the layer).

## 2. How it was made

- Source: the movement layer's extracts of the 321 answers in `public/viden/movement-index.json` (the local
  `.cache/movement` extracts, keyed by nr exactly as build_movement.py maps them), counted per concept in the Danish
  extracts and in the original English and Arabic texts. Where a sentence's wording mattered (a quotation, a
  classification, who did what), it was read against the original answer and corrected: e.g. the 'peace through
  strength' wording of one answer is only in its question (left out), a capitalism quotation belonged to an older
  answer (moved), Russia's 2015 Syria intervention and veto (31/10/2022) is the Arabic original's own wording.
- Only what the answers say, never a reading of our own; a classification follows the newest answer (Russia a middle
  power 12/6/2026, Iran a satellite state again 28/6/2026, Britain weakened 5/8/2026, Turkey revolving around the US as a
  NATO member 18/8/2026, China a regional power 22/11/2025). Where a newer answer only touched a concept in passing,
  it was left out rather than made to look like the newest reading.
- Khabar's content rules on every text: 'Israel' in our own voice (the movement's term only in a quotation, none
  needed); no praise of or call to violence; states, rulers, policies and ideas are judged, never peoples or religions
  ('jøderne' → 'det jødiske folk'; 'kurderne', 'de græske cyprioter', 'tyskerne' → the leaders, the side, the state);
  no non-ruling person, Danish person or organisation, mosque, scholar or media outlet said to serve a power (such
  clauses were dropped or turned into the state's own act: 'sine folk i Ukraine' → 'sin indflydelse i Ukraine'); no
  conspiracy myths; no deadly attack said to be staged; quotations at most 60 characters; no full answer texts.
- Dropped candidates: Sinai, the Durand line, the Jeddah talks, Frankofonien, the Taif agreement and the GCC – too few
  answers, or held by another page (Frankofonien sits in Commonwealth's and kolonialisme's rows).

## 3. Decisions on ids and aliases

- **No state, power, group or issue id** except `nato`. The layer's NATO page holds one reading (22/11/2010); the
  concept has 22 answers to 18/8/2026, so it replaces that page on purpose (the merge reports the id clash). It keeps
  `subject: nato` and kind `organisation`, which the other part's tests require.
- **Verdensordenen, not 'den-internationale-tilstand'.** That id is the layer's issue page (117 answers, a sag the tests
  require); a concept of the same id would replace it. The concept 'Verdensordenen' explains the movement's term
  (the great powers' stance towards each other and towards the leading state) and holds the Danish forms
  ('verdensordenen', 'den internationale orden', 'multipolær verden', 'den internationale situation/tilstand'); it
  links the issue page, and the merge links back.
- **Aliases (355)** are the Danish news forms, base form only (the linker adds the possessive), and pass the other
  part's alias rules: no ordinary Danish word, no adjective, no word for a people (dropped: 'sanktioner',
  'demokrati(et)', 'føderation', 'kapitalistisk(e)', 'nationalistiske', 'baluchiske', 'uighurer', 'uigurer'; Donetsk and
  Luhansk only as 'Donetsk-regionen' etc., since single words ending in -sk are refused). Case-insensitive where Danish
  news varies the case (Nato/NATO, Opec/OPEC): the merge keeps one case form of a concept's aliases, so a
  case-sensitive page would lose 'Nato'.
- **Forms that would link the wrong story were removed**: 'statskup' (said of parliaments), 'terrorbekæmpelse',
  'kampen mod terror' (Danish domestic counter-terrorism), 'politisk islam', 'radikal islam', bare 'normalisering' and
  'normalisere forholdet' (now '… med Israel'), 'uafhængig stat', 'guldstandarden' (the idiom), 'Camp David' (the
  retreat), 'Trumps fredsplan' (the 2025 Gaza and Ukraine plans), 'Doha-forhandlingerne' (the Gaza talks),
  'Lausanne-aftalen' (the 2015 Iran framework), 'Trump-doktrinen', 'den første stat', 'Genève-konferencen',
  'Sverige-aftalen', 'Bahrain-konferencen', 'politisk plan'.
- **Page names link too** (build_begreber matches a page's name with its aliases), so names that are ordinary words were
  made specific: 'Sanktionspolitik', 'Demokrati og demokratisering', 'Normalisering med Israel'.
- **The OSCE Minsk Group is not the Minsk agreements**: the group's answers (5/10/2020, 16/8/2025) and the alias
  'Minsk-gruppen' are on the Karabakh page; Minsk-aftalerne holds Ukraine only.
- **Alias clashes the concepts win on purpose** (the more specific page; the merge reports each): FN, De Forenede
  Nationer, FN's Sikkerhedsråd, Sikkerhedsrådet, Den Internationale Straffedomstol and ICC (from fn-og-folkeretten,
  which keeps Den Internationale Domstol and ICJ), Karabakh and Nagorno-Karabakh (from kaukasus), Vestsahara (from
  nordafrika), Darfur (from sudan-sagen), Monroe-doktrinen (from det-amerikanske-kontinent). Gaza and Vestbredden,
  which the other part left for a future place page, are here.

## 4. Measured

- 90 pages · 647 timeline rows · 937 answer links over 274 of the 321 answers · 355 aliases · 294,528 bytes. Most
  answers: kolonialisme 25, Brexit 23, satellitstat 22, NATO 22, krigen mod terror 22, Verdensordenen 21, sanktioner 21,
  normalisering 21, IMF 21; fewest: den dybe stat 1, fred gennem styrke 2.
- The builder's check (attribution to the row's own answer and day, every nr in movement-index.json, newest answer in
  the lead, at most four lead sentences each naming Hizb ut-Tahrir, ids unique and kebab-case, aliases unique
  case-folded, related ids are pages, build_movement's voice rules H1/H3/H4/H5 and the staged-attack and serving checks,
  quotations, private paths): 0 problems. An independent check of the written file: 0 problems.
- The other part's merge, run in memory on the file: no concept, alias, answer or related id left out or dropped;
  one id clash (nato) and the eleven intended alias clashes; `check()` of the merged wiki 0 problems; 203 pages
  (114 + 90 − 1).
- In a scratch copy of the branch: `py scripts/build_begreber.py` with this file, then the whole suite: 113 passed,
  6 skipped. In the worktree, until begreber.json is rebuilt, one test fails by design
  (`test_the_build_works_without_the_concept_file_and_the_committed_wiki_is_the_build`: 'begreber.json is out of date').
- Link test on the live radar (2,369 Danish texts: titles, summaries, search, editor lines; longest alias first): 241
  links to 19 concepts – Gaza 110, Vestbredden 55, Jerusalem 20, Hormuzstrædet 15, FN 11, NATO 10, Det Røde Hav 4,
  FN's Sikkerhedsråd 3 … Before the removals above the test also linked 'sanktioner' in a Danish haulage story,
  'statskup' said of a parliament and 'demokrati' in general; after them the one wrong link left is Jerusalem inside
  outlet names (10 of 18 texts: 'Jerusalem Post', 'Jerusalem Daily').
- The radar's weighing (src/radar/method.py) with the rebuilt index against the committed one, 623 stories: no tier
  changed; four stories gained the actor den-internationale-straffedomstol (ICC). The organisation pages become actors.

## For the other parts

- **Rebuild the wiki**: `py scripts/build_begreber.py`, then commit `public/viden/begreber.json` and
  `begreber-index.json` (not this part's files) – the merge and the suite are clean with this file.
- **The linker** should mask outlet names before it links (the sources in config/feeds.json: 'Jerusalem Post',
  'Times of Israel' …): a page name inside an outlet's name is no mention of the place or state.
- These pages are written, not built: a new answer that reads a concept needs its row (and, when it governs, the lead)
  here. The editor's answers.json can name these ids in `begreber`. A page a concept replaces (nato) no longer shows
  the layer's newer readings or relations: if the layer gains a `nato--x` relation, the concept must carry it, or
  `test_a_relation_is_on_both_parties_pages` fails.
