# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

## [Unreleased]

### Added

- Project scaffolded from the `web-app` workspace template.
- Radar that reads ~50 sources (RSS, Google News, Telegram, YouTube) every 5 minutes.
- Relevance scoring against the group's shared links with a multilingual language model.
- Same-story grouping, big-story detection and one-notification-per-story pushes.
- Automatic self-learning from community sources, big stories and copy taps.
- iPhone home-screen app with copy button, tabs, search and notification sign-up.
- 11 more Danish sources; liveblog/sport/celebrity filter; at most 4 'Vigtigste' cards per source a day.
- Trust labels: 'Bekræftet af N medier' / 'Ubekræftet · kun Telegram/YouTube'.
- Optional Danish mode (offline English-to-Danish translation, WhatsApp-ready copy with bold headline).
- Arabic/Turkish setting: translate, hide or show original.
- Claude editor routine writes 'Dagens overblik' at 07 and 17 to the `digest` branch; the app shows it and notifies.
- Claude caretaker routine checks the radar daily, repairs or disables broken sources, logs to docs/radar-status.md.
- Stale-data warning in the app; per-source failure counts; manual push-test workflow.
- Renamed the app to Nabd with a pulse icon; compact, text-first, minimal list design (headline + one meta line
  with small indicators, relevance bar, tap to expand, copy icon and swipe-to-copy).
- Big stories now also need clear relevance (80th percentile) before they are shown or learned from.
- Thumb-first layout following Apple's HIG: bottom tab bar (Vigtigste, Alle, Kopieret, Søg, Mere), search field
  above the keyboard, 44pt+ touch targets, 'Mere' sheet with drag-to-close and a bottom 'Færdig'.
- Purposeful motion: ECG-line pull-to-refresh, gliding tab indicator, height-animated expand, copy icon morph,
  wash on newly arrived lines, '↑ N nye' pill, staggered first paint; all off under Reduce Motion.
- 'ny' marker for lines that arrived since the last visit.
- Renamed the app to **Khabar** (خبر, "news") with a bold K icon; black/white/red look.
- Appearance settings: five tones of the same look (Klassisk default, Blød, Papir, Kølig, Dæmpet), each with
  light and dark versions, plus Automatisk / Lys / Mørk. Applied before first paint, so no flash.
- Swipe background now only shows while swiping (no red hairlines between lines).
- New default look "Papir": warm paper colour with a fine grain, black ink and red, in light and dark.
  The other tones (Klassisk, Blød, Kølig, Dæmpet) remain in 'Mere'.
- New icon and logo: the word خبر in Lalezar on warm paper with the red dot over the خ; in the app the dot
  is the live pulse. Icon renderer kept in scripts/icon/.
- Motion design on paper and ink: an opening where خبر is written right-to-left and the red dot drops in before
  the logo flies into the header; lines printed in from an ink blur; a red 'KOPIERET' stamp when copying;
  pull-to-refresh as an ink drop that splashes into ripples; tabs slide in the direction of travel; lines unfold
  like paper; the overview rule draws itself; big-story markers throb once; the logo settles when scrolling.
- Dark mode now uses proven palettes instead of the brown paper-dark: Varm grafit (default), Material, Apple and
  Notion, chosen under Mere → Udseende → Mørk, independent of the light tone. Lighter secondary text.
- Big stories must also clear a cross-language relevance bar (72nd percentile), so widely covered off-topic
  Danish stories (e.g. northern lights) no longer qualify.
- **Sections.** Every story is placed in Danmark, Mellemøsten or Verden from the places, parties and people it
  names (config/sections.json); stories without telling words follow the closest placed stories, their language
  and their source. The app's tabs are now Forside · Danmark · Mellemøsten · Verden · Søg.
- **New ranking.** A story's rank = the group's taste + up to 20 for the number of established outlets + a lift
  for the group's core subjects, biggest for Danish politics, Islam/Muslims and immigration (Danish politics was
  being cut because the group's links are mostly about other countries). Weather, sport, royals and everyday
  crime are pushed down; headlines that name nothing lose a little. Each section shows its own top ~15 %.
- Danish stories must touch politics, Islam/Muslims or immigration (or lead most Danish front pages) to be shown.
- A political story carried by most Danish outlets counts as a big story ("Stor historie i Danmark").
- The same story told by a Danish and an English outlet now becomes one card (second look at the cards).
- Coverage view: an opened story shows how Danish, Western, Arab/Muslim and Israeli media and the channels
  each tell it, one article per outlet, with counts per kind of media; Arabic and Turkish headlines there are
  machine-translated.
- Front page: 'Netop nu' (big and very fresh important stories), Claude's overview, and the best 4 stories of
  each section (at most one per source, unconfirmed channel posts last).
- Section pages: 'Vigtigst lige nu' then everything else by day.
- Search covers everything the radar read in the last two days (search.json), not only the shown stories.
- Sharing uses the phone's own share sheet (WhatsApp is one tap away), with copy as a second button;
  opening and sharing silently teach the radar (opening counts less).
- Busy Telegram channels show at most 6 lines a day; their alarm emoji and 'Breaking |' tags are removed.
- Liveblog teasers ('følg med her', 'se med her') are filtered out.
- Claude's overview is grouped by section with at least two Danish stories when there are any.
- `scripts/rank_check.py` shows what each section would contain with the current settings, on live data.

- **Bevægelser** (new tab): political movement in the format members of the group post themselves – topics with
  short attributed statements ("Kremlin: ..."). Claude writes it at 07 and 17 from the radar's statement lines,
  ready to share to WhatsApp; under it the newest lines from Al Jazeera's urgent wire, machine-translated.
- New source: Al Jazeera's Arabic urgent wire (Telegram `ajanews`), the lines members translate for their
  briefings. A wire line counts as an outlet on a story and feeds 'Bevægelser', but is never a card of its own.
- `lines.json` on the data branch: one-line statements of the last 36 hours (wire lines, channel posts and
  headlines that are one statement by a named actor), with English and Danish machine translations.
- The taste profile now also learns from the ~900 statement lines in the briefings members posted without links
  (no member names are kept); actors from those briefings added to the section words.
- Arabic source names are shown in Latin script (Al Jazeera (arabisk), Sky News Arabia, BBC Arabic …).

### Changed

- Claude now works at 07 and 22 (was 07 and 17) and writes both things in the same run: the overview, where
  every story has a 2–3 sentence summary of the article (Claude reads the article when it can), and a new
  edition of Bevægelser – the whole Al Jazeera breaking wire of the period, translated by Claude.
- Bevægelser is a growing list: each edition is added on top and the earlier ones stay (moves.json on the
  digest branch, 30 editions). The machine-translated live list that changed every five minutes is gone.
- Front page: Claude's overview on top, then every story as it comes in, all sections mixed and marked with
  their section (replaces 'Netop nu' and the section blocks).
- Short explanations on the overview and on Bevægelser of what they are and when they update.
- Search moved to a magnifier in the top bar; the fifth tab is now Bevægelser.
- Sharing is one action among three (Læs, Del, Kopiér) inside an opened story instead of the centre of the app.
- Quiet, short motion instead of the paper-and-ink effects: no opening animation, a neutral ring for
  pull-to-refresh, a calm confirmation pill, rows that rise in gently and a soft wash on new stories.
- Clear words instead of symbols in the list: 'Stor historie', '7 medier', 'ubekræftet', 'oversat', 'delt'.

### Fixed

- Machine translation of Arabic got names wrong ("Island correspondent" for Al Jazeera, "Trimpe", "Butin"); a name
  glossary fixes them before and after translating.
- A new Bevægelser briefing now shows even when the overview itself is unchanged.
- Unrelated Arabic headlines were merged into false 'big stories' (the language model puts some Arabic texts
  almost on top of each other); Arabic-only stories are no longer merged, and a story's card now comes from an
  established outlet rather than a Telegram post whenever one carries it.

### Removed

- The 'Kopieret' tab, swipe-to-copy, the red 'KOPIERET' stamp, the ink-drop pull-to-refresh, the splash
  animation, the relevance bar and the guessed 'learned' lines (word overlap with earlier copies).

---

<!--
Release entries look like this, newest first:

## [1.0.0] - 2026-01-15

### Added
- The thing that is now possible.

### Fixed
- The thing that used to be broken.
-->
