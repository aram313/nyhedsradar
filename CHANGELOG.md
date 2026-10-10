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
- Big stories must also clear a cross-language relevance bar (72nd percentile), so widely covered off-topic
  Danish stories (e.g. northern lights) no longer qualify.

---

<!--
Release entries look like this, newest first:

## [1.0.0] - 2026-01-15

### Added
- The thing that is now possible.

### Fixed
- The thing that used to be broken.
-->
