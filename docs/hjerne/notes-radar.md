# The radar: the brain in the selection of news (2026-10-17)

Part of the hjerne branch. The owner's decision of 2026-10-17: the new understanding is used **only when news is
chosen**. So the radar weighs and selects by the books' order of importance and Hizb ut-Tahrir's newest readings of the
powers; nothing of it is shown as an analysis. Commits: `c493bc3`, `50e83b3`, `6e3aa92` and the one with this note.

## What the radar does now

**1. Camps and 31 more sources** (`config/feeds.json`). Every source has a `camp` (the state or bloc whose view it
carries; `voice: officiel` on Anadolu), ported from Khabar 2 onto this branch's file (no caretaker change since
893182f, so nothing of the caretaker's was lost; order and format kept). The 31 sources Khabar 2 added follow at the end
– TASS, Kremlin, Russia's MFA, CGTN, Xinhua, Global Times, IRNA, Al Mayadeen English, Asharq Al-Awsat, SPA, Ahram, The
Hindu, India's MEA, the European Commission, the White House, the State Department, the UK FCDO, UN News, Daily Sabah,
TRT World, APP, Ariana, AKIpress, AllAfrica, WAFA, Enab Baladi, Shafaq, Antara, SVT, NRK, Le Monde – each with
`"scale": false` (below). The movement's own outlets (HT Arabic, Köklü Değişim) have group and camp `bevægelsen`.

- Probe from this PC, 17/10 about 01:00 Danish time: 30 of 31 answered. Enab Baladi's own feed refuses Python's fetch
  (HTTP 403, curl gets 200 – a fingerprint block), so it comes through Google News (`site:english.enabbaladi.net`,
  7 items that day). Their feeds held about 870 items from the last 24 hours; several hold only their newest 10–100, so
  polled every five minutes they will bring an estimated 1,000–1,400 items a day on top of today's ~2,600.
- SVT and NRK are Swedish and Norwegian: there is no sv/no translation model, so their headlines stay as they are
  (readable for Danes, as the Khabar 2 review said) and are never notified.

**2. The added sources never move the scale** (`scale: false`, run.py). The radar's whole calibration (taste percentiles
per language, each section's bar, the outlet lift of the rank, big stories) was set on the 62 established sources. A
source added for its camp is placed on that scale without moving it: percentiles are computed against the established
sources' items only; a section's bar against stories an established source carries; the rank's outlet lift and the big
rule count established outlets only (`_ref_out`, `_ref_est`, internal). The added sources still count as outlets in
`outlets` and `confirmed` (they are established outlets), show in a story's coverage and `camps`, and each may lead at
most `max_added_per_day` = 3 cards of its own a day (settings.json; big stories exempt). They lead a story only when no
established source carries it, so the cards keep the outlets the group knows. A test proves the scale stays put:
120 low-taste TASS items leave every percentile and the shown set unchanged (and the test fails without the guard).

**3. The movement's own outlets** never count as an outlet or as confirmation (a lone post of theirs is `confirmed: 0`,
like a channel's), never lead a story another outlet carries, and are still in the coverage (group `bevægelsen`).
Governments' own channels (group `official`) never lead a story others carry either.

**4. The brain: 13 tiers** (`src/radar/method.py`, `config/method.json`, `tests/test_method.py`). Each story gets the
heaviest tier its headline shows (original, English and Danish versions; 'ignore' phrases such as "Liberal Alliance" taken
out first). The powers follow the movement's newest readings (method.json `_why`, every reading attributed and dated):

| | the power | why (Hizb ut-Tahrir's newest answers) | in the tiers |
|---|---|---|---|
| leading | USA | 14/1/2026 (28942): the leading state, no state challenges it | its acts: tier 2; with another power in one act: tier 1 |
| great | Britain | 5/8/2026 (30093): only the Gulf states and Jordan left; 27/9/2026 (30420): the USA pushes its last forces out of Yemen | a weakened great power: tier 3 |
| great | France | 24/7/2024 (26393), 16/8/2025 (28073): losing Africa to the USA, marginalised in the Caucasus | a weakened great power: tier 3 |
| power | Russia | 12/6/2026 (29773): fallen to a middle power, courting the USA; 19/8/2025 (28095): Alaska a US dictate | no great-power tier; its acts are the Europe issue (tier 5); its dealings with the USA tier 1 |
| power | China | 22/11/2025 (28627): an independent regional state that only reacts; 12/6/2026: did not rescue Russia | its acts are the Far East issue (tier 5); its dealings with the USA tier 1 |
| actor | Germany | 23/6/2023 (24744): orbits the USA, builds an army; 28/10/2010 (7980): »reelt ikke en stormagt« | no power: an actor of the Europe issue |
| actor | EU | 2/5/2025 (27671), 28/6/2025 (27867): kept out of the Iran file; 1/3/2023 (24296): united under US leadership | no power; its sanctions are an instrument (tier 7) |

The tiers (lift = rank points; bypass = reaches the editor below the taste bar):

| tier | what | lift | bypass |
|---|---|---|---|
| 1 | the leading state with another power in one act (agreement, summit, war, sanctions, talks, tariffs) | +10 | yes |
| 2 | the leading state's acts – with another state, group or organisation named, or an act aimed outward by nature (war, sanctions, tariffs, troops, arms) | +8 | yes |
| 3 | a great power's acts (Britain, France), on the same condition | +6 | yes |
| 4 | who controls a state: coup, succession, regime change, a ruler ousted or killed (abroad, or naming a state other than Denmark) | +6 | yes |
| 5 | the major issues: a story in Mellemøsten, or naming a state of the six issues (Europa, Centralasien, the subcontinent, Fjernøsten, Afrika) | 0 | no |
| 6 | the campaign against the belief and the concepts (mosques, imams, hijab, Quran burnings, curricula, 'moderate Islam', Muslim Brotherhood labels, Uyghurs; in Danmark also Muslims and Islam) | +6 | yes |
| 7 | instruments: the Security Council, courts, international law, NATO, sanctions, IMF/World Bank, summits | +3 | no |
| 8 | an exposure: leaks, secret documents | +3 | no |
| 9 | colonial and economic interest: oil, gas, straits, ports, minerals | +1 | no |
| 10 | military acts | 0 | no |
| 11 | the rest (international, outside the method's frame: US domestic news, shootings, Western domestic) | −4 | no |
| 12 | a Danish story that cannot be placed internationally | 0 | no |
| 13 | weighed down: light news, and ceremony (state visits, condolences, congratulations) when nothing of tier 1–4 is in it | −8 | no |

Decisions behind the numbers:

- **A lift only for what an established outlet carries.** The first trial gave the lift to everything, and two
  unconfirmed Clash Report posts jumped into Live's top 40 (one a quote about Chechnya in the 1990s). Now positive lifts
  need `confirmed ≥ 1`; negative ones always apply.
- **Tier 5 lifts nothing.** It covers more than half of all stories; at +2 it pushed every Danish story (tier 12) two
  points down against the Middle East, and "Messerschmidt: Jeg anker ikke" fell out of the top 40. At 0, Danish politics
  holds its place and the reordering happens among the sharp tiers and tier 11. The Danish lift (`rank_core_dk`) and the
  dk-section rules are untouched.
- **Russia and China no great-power tier**, following 12/6/2026 and 22/11/2025: a Russian–Iranian military pact or a
  China–Russia treaty is tier 5, not 3; only their dealings with the USA are tier 1.
- **No act of a power without a foreign actor or an outward act.** Without it, "UK court rules on ITV broadcasting
  deal", "US solicits oil from its strategic reserve" and French school protests were tier 2–3.
- Word traps found on the live data and closed (each has a test): `*krig` found "Fran-krig" (every France story was tier 3),
  `islam` found Islamabad, Arabic انقلاب is also "overturned" (a vehicle), `*strategi` found "strategic reserve", "war-like",
  school "blockades", "recognition" (UK law), Danish "afsat/styrtet" (allocated/crashed), "attentatplaner" in a Danish court case.
- **The bypass**: tiers 1, 2, 3, 4, 6, an established outlet carries it, not light news, rank ≥ 45, at most 20 a day
  (by the day it was found), the strongest first; such a story carries `method: true`. On the snapshot: 20, 17 and 14 on
  the three days – mostly the USA's acts on Iran (blockade, sanctions), Trump's Gaza plan, the UK's sanctions on
  settlements, the Muslim Brotherhood label Trump put on a US Senate candidate, a coup leader turned president in
  Myanmar.
- Weighing every lead costs about 2 seconds a run (a substring test before each regex list made it 7× faster).

**5. Actors** (`actors`): ids as in `public/viden/movement-index.json` and the wiki – ~75 states, groups and
organisations in method.json with Danish, English and Arabic forms (no persons except rulers' names as their states'),
plus the wiki's own Danish names from `public/viden/begreber-index.json` (kinds stat, magt, gruppe, organisation; as
whole words, so "Mali" never finds Malibu). So a story's `actors` point straight at wiki pages.

**6. The movement's new answers** (`src/radar/analyses.py`, `tests/test_analyses.py`, `RADAR_ANALYSES: '1'` in
radar.yml; the Energy prices step kept). The list page is read every 3 hours; the text of at most 3 new answers a run is
fetched – **only of answers not in movement-index.json** (`known`): the static layer holds the rest, and a text leaves
the state once the next build holds the answer. Checked against the live site 17/10: 8 answers listed, the newest 30420
(27/9/2026), all already in the static layer – so no text is fetched today. `data.json` gets `analyses`:
`[{id, title, date, url}]` of new answers whose text the radar has (today `[]`).

**7. No knowledge model**: no case placement, no chains.json, no RADAR_KNOWLEDGE, no model branch. Khabar 2's admin
'decide' (approving model changes) is not ported.

## One Live list – counts and caps

The per-section rules stay: each section's bar (top 15 % of its own stories on the established scale), the rank floor,
the unconfirmed cap (an eighth of a section), 6 posts a day per channel, 4 'important' per source a day. Because the bar
is per section, Danmark keeps its share of the pool however the international sections move. New: 3 own cards a day per
added source, 20 a day through the method.

| snapshot 16/10 22:50 UTC | shown, 72 h | Live, 24 h | Danmark | Mellemøsten | Verden |
|---|---|---|---|---|---|
| origin/main radar | 630 | 181 | 31 | 74 | 76 |
| hjerne radar | 669 | 197 | 31 | 83 | 83 |

The +16 a day are the bypassed stories. The added sources' own cards are not in these numbers: the snapshot has no items
of theirs and nothing can be embedded locally (no fastembed here), so their effect shows only on the live radar. The
bound by construction: 3 own cards a day each (31 × 3 = 93 at the very most; my estimate 25–40, mostly TRT, Daily Sabah,
Asharq, Al Mayadeen, TASS, Xinhua, Global Times, The Hindu). **Watch after the first day** (the quarter-hour check or the
caretaker): Live's 24-hour count (now ~200), the cards led by a `scale: false` source, and their failing runs. Lower
`max_added_per_day`, or disable a source, if Live floods. With the owner's volume rule (notes-owner-volume.md) the
editor admits from this pool; the radar's list is Live only in the fallback.

## Live's top 40 before and after (the snapshot, 'Vigtigste': last 24 hours by rank)

`py scripts/rank_check.py` with `RANK_CHECK_STATE` on the same saved snapshot for both (origin/main exported with
`git archive`); the profile is the cached snapshot `c6b3ba17414b` for both.

Into the top 40:
- #75 → #21 (tier 1, the USA and Russia in one act): "US lawmaker introduces bipartisan bill to block Trump
  administration's Russia diesel deal" (Anadolu).
- #82 → #34 (tier 2, the leading state's act on Israel): "Trump backs Israel unity plan keeping Netanyahu PM for two
  years after election: Report" (The New Arab).

Out of the top 40 (just below): #38 → #41 "Politikere jubler – fynsk milliardær investerer i sjællandsk provinsby"
(local), #39 → #43 a West Bank raid (tier 5, unchanged rank; the two risers passed it).

Within the top 40:
- up: the Danish debate on a Muslim influencer and Pia Kjærsgaard #4 → #1 (tier 6: the campaign against Islam and
  Muslims in the Danish debate, which the editor also picked); "Trump giver Zelenskyj skylden for stigende dieselpriser"
  #40 → #14 (tier 2).
- down: US domestic news (tier 11): the US school shooting #8 → #11, Trump's message to his spokeswoman #12 → #20,
  "Trump fyrer nyansat talsperson" #15 → #25.
- **Danish politics**: 10 → 9 in the top 40 (the one that left is the Funen investment story), 7 → 7 in the top 20; the
  first eight Danish political stories stood at #4, 13, 14, 16, 17, 18, 19, 27 and now at #1, 12, 13, 15, 16, 17, 18, 29.
- The editor's eight picks of 16/10 22:03 UTC (one is older than 24 hours): at #2, 60, 28, 3, 37, 4, 14 before and
  #3, 63, 30, 4, 40, 1, 13 after – the two new tier-1/2 stories pass most of them by a place or two.

## The movement's current focus – tested, not kept

A lift for stories naming the states Hizb ut-Tahrir's answers of the last 120 days dealt with (30420 Yemen, 30170 the
tripartite alliance, 30093 Iraq, 30066 Sudan, 29870 Iran):

| variant | Danish politics in top 20 | first eight Danish political stories at | editor's picks at |
|---|---|---|---|
| without (kept) | 7 | 1, 12, 13, 15, 16, 17, 18, 29 | 3, 63, 30, 4, 40, 1, 13 |
| all their states, +3 | 6 | 2, 14, 15, 16, 19, 20, 22, 38 | 3, 73, 23, 4, 31, 2, 15 |
| all their states, +6 | 3 | 4, 17, 19, 24, 27, 28, 30, 41 | 2, 82, 18, 3, 26, 4, 19 |
| main subjects only (Yemen, Houthis, Iraq, Sudan, RSF, Iran), +4 | 6 | 2, 13, 14, 16, 18, 20, 21, 31 | 1, 69, 19, 4, 40, 2, 14 |
| main subjects without Iran, +4 | 6 | 1, 12, 13, 16, 18, 20, 21, 31 | 3, 67, 19, 4, 40, 1, 13 |

The answers' states are practically the whole Middle East (Israel, Iran, Saudi Arabia, Turkey, Egypt, Lebanon…), so
the broad lift raises the Middle East as a block – an Israeli opinion piece as much as the Houthi attacks – and pushes
Danish politics down (at +3, 26 more stories over the bar in 72 hours, 24 of them in Mellemøsten). The narrow lift moves the Houthi story up (#30 →
#19) and nothing in or out of the top 40, at the cost of Danish politics slipping. Not a clear improvement, so it is
off and its code was taken out (no dead option). The editor's front page can still follow the newest answers.

## For the app and the editor

- New fields on every story in `data.json`: `members` (every member id – the editor admits a story by any of them),
  `camps` ({camp: members}), `first` ({source, camp, published}), `actors`, `tier`, `tags` (every tier the headline
  shows), `powers`, `method` (true when only the method brought it in); in `also[]`: `camp` and `published`.
  The app shows none of it as analysis; `tier` and `outlets` drive the app's provisional Live (tier ≤ 2 with ≥ 2 outlets).
- New `group` values: `east` (Russian, Chinese, Indian and Central Asian media), `official` (governments' own
  channels), `bevægelsen` (the movement's outlets). Today's app filters by its GROUP_ORDER, so they are silently left out
  of the coverage view and the sources list until the app names them (Khabar 2's labels: 'Russiske, kinesiske og indiske
  medier', 'Regeringers egne kanaler', 'Bevægelsens egne kanaler'). `cover` may carry these keys too.
- Preview of today's real data: `.cache/hjerne-preview/data.json` and `lines.json` (the live state of 16/10 23:34 UTC
  run through this radar; no analyses.json – none on the data branch yet).
- `scripts/brain.py` (the editor's) imports `Method().weigh(it)[0]` as a fallback tier; the API is
  `Method(cfg=None, wiki=None)`, `weigh(it, trivia=False, actors=None) -> (tier, tags, powers)`.

## Open points

- **Texts on a public branch:** the text of a *new* answer sits in `state/analyses.json` on the public data branch until
  the next static build holds it, because the editor routine has no internet. Khabar 2 kept 40 such texts there; this
  keeps only the new ones. If the owner wants no copy at all in the public repository, the text would have to be
  encrypted with a key the routine holds.
- The added sources' real effect on Live (above) – watch the first day.
- The tiers read headlines only; a story's first pass sees only its original language (English and Danish versions come
  with the next pass). Arabic word lists are short.
- Pre-existing, not changed: "Ny demonstration i Albanien" sits in Mellemøsten (the sections' placement).
