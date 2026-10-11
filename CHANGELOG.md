# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

## [Unreleased]

- The Udvikling page is one view instead of two (Forløb / Resumé), as the owner chose: 'I dag' with 'Del resumé' at the top, then the day's topics in the editor's order – each a card with the day's lines, newest first, that unfolds into the whole development across the days – then the developments of the last days that today has not touched, and the earlier days at the bottom. Every line shows once; the switch is gone.
- On a PC the middle mouse button scrolls the page as on ordinary sites (the browser's own autoscroll does not reach the app's fixed pager): hold and move, or click and move; any click or Esc stops it. A link still opens in a new tab with it. On a wide screen the wheel and the middle button work anywhere in the window, also beside the app's column (before, only over it).
- Fixed: on iPhone the steps of 'Sådan udviklede det sig' (Dagens historie) and of a development could not be tapped. Each step is now a real button (a story: opens it in Live) or link (a wire statement: opens its source) across the whole row.
- The editor updates twelve times a day instead of three, as the owner chose (07, 10 and 13, then every hour from 15 to 23 Danish time): each update is small – at most 5 recap lines, 6 summaries and 8 headlines, only what is new since the last – and only the first update after 21 notifies the phones. The app says the recap is updated 'løbende fra morgen til aften'.
- Fewer Claude tokens for the editor, as the owner chose: it reads ~40 % less (40 top stories instead of 70, yesterday's recap only as topic names after the morning, no story listed twice), writes 15 summaries instead of 25 (the stories readers opened first) and checks 20 headlines instead of 40; it no longer tries to open articles or find pictures (its cloud has no internet, and the owner prefers the initials tiles); and it runs only three times a day (05, 13, 19 UTC – an hour earlier in winter) instead of six with three idle starts. The app says the recap comes 'morgen, eftermiddag og aften', and a summary's note says it rests on the headlines and the outlets' introductions.
- Fixed: in search, the group bands ('På Khabar', 'Andre nyheder') did not stay at the top of the results while scrolling; they stuck at the top bar's height, inside the results box under the search field. They stick to the top of the results now.
- Fixed: on iPhone the top of every page (the date on the front page) lay hidden under the top bar. The pages took the bar's height from a measurement that did not always come, and fell back to a height without the status bar; the bar's height is now computed in the stylesheet (status bar + 50 pt), and the tabs' likewise.
- Pull to refresh needs a deliberate pull (130 px instead of 84): a little extra drag at the top of the page to see the date no longer refreshes it.
- Fixed: headlines showed plainly under the logo while scrolling – iPhone no longer blurs what passes under the translucent top bar over the pages; the bar is solid.
- The Udvikling page's switch stays under the top bar while one scrolls, and its second half is called 'Resumé', so the recap is easy to find.
- Fixed: opening an earlier day under Dag for dag left the page in the middle of it (the recap above folded); the opened day now starts just below the top bar.
- The Udvikling page no longer stacks the recap and the developments (the same lines twice, in two kinds of box): a switch at the top shows one way at a time – 'Forløb', story by story across the days, or 'Dag for dag', the day's recap ready to share and the earlier days. A development opens Forløb; the recap notification opens Dag for dag.
- Pictures for the strong stories that had none: the radar now tries the share picture of every outlet's article page (up to five), not only the first one's; and three times a day the editor looks for a picture for up to 12 strong stories still without one – the story's own from an article page, else a freely licensed Wikimedia Commons photo of the person or place, which the app tags 'Arkivfoto' and credits in the opened story (never another event's photo, a drawing, an AI picture or the dead and wounded; no picture rather than a wrong one).
- Every story row (not Live's ticker) has its picture place: where a story has no picture, or it cannot be loaded, the outlet's initials (DR, BT, P, AJ …) stand on a quiet tile in the newspaper type; the big cards do the same instead of an empty box.
- Fixed: opening or closing Dagens historie made its headline and dark fade vanish for a moment on iPhone, which redrew the picture's layers while its colour glided from 15 % to 30 %. The colour now changes at once. (A first try that locked the layers instead hid the headline altogether on iPhone; it is undone.)
- Fixed: opening a story while one above it was open made the page leap up and then crawl back down to the story. iPhone now keeps content in place by itself (scroll anchoring) on top of the app's own correction, so the page moved twice as far, and the reveal used the browser's smooth scrolling, which crawls on iPhone. Scroll anchoring is off on the pages, the tapped story is held where it was while the ones above fold (through their animation), and an opened story that reaches past the tabs comes up with a short motion of the app's own – never with its headline under the top bar.
- Fixed: lifting the finger between two tabs on the tab bar sometimes let the pages crawl to a tab in slow motion (the browser's own smooth scrolling on iPhone). They now snap to the nearest tab in about a fifth of a second, with the app's own short motion; a finger on the pages meanwhile takes over.
- UX review, as the owner chose it: the intro writes the name only on the first visit and after six hours away (else straight in); five tabs – Udvikling is a page of its own (from the front page, the stories and search; the logo, with a back mark, returns) holding the recap, every development and the earlier days; the front page is shorter (no section glance, no recap there) and gains 'Følg udviklingen' (the three developments that moved last); foreign headlines are shown in Danish by default, the strongest gone over by the editor three times a day (summaries.json `titles`), the opened story naming the original; text size follows the phone or the new setting (Som telefonen, Normal, Større, Størst), rows growing with it; settings start with notifications and fold the colour palettes under 'Flere farver'; 'Live' is the one name (no 'Live feed', no 'Lige nu'); old news shows only the box on the page, not also a red top bar; shared texts end with 'via khabar.nu'.
- Fixed: the intro's pen wrote over letters that were not there yet. Since the font loads beside the page, the intro asked for it before Google's font sheet had arrived, found no such font and began at once; it now waits for the sheet, then the letters (at most 2.5 s, then the word simply shows), and the phone keeps the font so later starts have it at once.
- Fixed: a white flash when the app starts on a dark phone. The phone shows its own surface while the app starts, white unless the page says at once that it has a dark look (color-scheme, set from the saved light/dark choice before anything else); and the start waited for Google's font file before drawing anything – the font now loads beside the page (the intro waits for it itself), and the app's own versioned files come straight from the phone. The tabs and the top bar stay hidden while the intro writes (their labels showed through on some starts).
- Fixed: the tabs at the bottom sat a status bar's height too high on iPhone's home-screen app (the page was made 100 % tall and held still, which iPhone measures without the status bar); the page is a full screen tall again. Fixed: a flash on opening the app and on coming back to it – the page's colour glided in from black at the start, and back from the light look iPhone draws for its app switcher; colours no longer glide while the app is away or when the phone switches between light and dark.
- Statistics for the owner, at the top of Indstillinger when the admin code is set (nobody else sees it): openings today, 7 and 30 days, new users, phones with notifications, openings per day (14 days) and per hour, home screen or browser, iPhone or Android, country (from the phone's time zone) and language, how people came in (notification, WhatsApp, Facebook/Messenger, Google, sms, other sites, straight), time in the app, the tabs looked at, and the most read and shared stories. Users notice nothing – no question, no button, nothing stored on the phone, no number that follows a person; the owner's own phone is not counted. The radar keeps the counts encrypted with a key from the admin code (state/stats.enc), so the public data branch shows nothing.
- Fixed: phones kept showing an old version of the app (only a private window showed the newest). The host lets a phone keep the page for ten minutes and the offline worker used that copy; it now always asks the server first (an unchanged file costs only a short 'not modified'). And an app left open in the background checks for a new version when it comes back and, if there is one, starts afresh with it (once per version).
- Sliding a finger along the tab bar now takes the pages along: they move as far between two tabs as the pill is (no snapping while the finger leads), the title and the bold tab follow the tab under the finger, and on lifting the finger the pages glide the last bit to that tab. During a swipe the bold tab changes with the title, at the halfway point. Pages that stop between two tabs are always brought home.
- The tabs are now real pages side by side in one horizontal scroller that snaps to whole pages, so the phone itself carries a swipe: the page follows the finger exactly and finishes at the finger's own speed with the phone's own easing and bounce at the ends, and nothing is drawn or swapped while it moves – the neighbours are drawn beforehand in a quiet moment – so the page cannot hop (before, a temporary copy was drawn about 15 px too low and jumped up when it became the page). Each page keeps its own scroll position; the pill and the title follow the swipe. The first pictures of every page load at once (also beside the page in view), the rest as the page scrolls near them.
- The tab bar has one pill that glides: to a tapped tab, part of the way along a page swipe, and under the finger when one slides along the bar – the tab under the finger lights up and opens when the finger lifts. Swipes no longer hop: the page cannot rubber-band, the pull to refresh only moves the list for a clearly downward pull, the page changes when the slide has really ended, and a neighbour shorter than its remembered scroll position is shown where it will stand.
- Every story's root is Live's chronological list: a step in Udvikling or in Dagens historie's timeline, a recap line and a Lige nu entry open the story there – opened and scrolled into view (older stories too). A step that is only a wire statement opens its source (↗).
- App: no hop when a swipe turns the page – the neighbour already drawn beside the page becomes the page (no redraw, pictures not loaded again, no title animation). Searching: the field sits under the top bar, the page stands still and only the results scroll, so the keyboard no longer pushes the page up.
- App: the title in the top bar says "Khabar.nu" on the front page, and the title keeps its room – the update status gives way first.
- Swipe left and right between the tabs (Forside, Danmark, Mellemøsten, Verden, Udvikling, Live), as in a native page view: the neighbouring tab lies ready beside the page and both follow the finger one to one; the direction locks after 12 px and a sideways swipe does not scroll; a flick (speed of the last ~90 ms) or a third of the width turns the page, which finishes at the finger's speed or springs back; at the ends it only gives a little; touches from the screen edge are left to the phone.
- Pull to refresh: the red dot of the logo in the top bar swells when the pull is far enough; let go and the list waits a little way down while the dot signals with the intro's hairline rings, and goes back up only when a full ring has finished (the name is not shown twice).
- One thing open at a time: opening a story folds the others (and an open card panel); those above it close at once and the page moves with them, so the tapped story stays put. Opening the recap or an earlier day folds the rest too.
- 'Lige nu' on the front page shows the three newest stories of the Live list (established outlets), and a tap opens that story in Live – before it showed raw wire lines and headlines that were nowhere else in the app.

- **Følg udviklingen**: a sixth tab, *Udvikling*, lists the editor's recap topics followed across days (headline, section, steps, latest statement); folded out, every step as a timeline by day. An opened story that belongs to one (it is a step itself, or shares five or more names and words with it) has a small *Følg udviklingen* button that opens the tab on that development.
- An opened story is short: the editor's summary (summaries.json on the digest branch, written at 07/15/21 for the stories readers open most; when the article could not be read, the editor's best reading and a note that Khabar had no access), Læs/Del/Kopiér, and two small buttons – *Følg udviklingen* and *Andre medier*, whose coverage list folds out only when asked for.
- Search suggests as one types: today's most-mentioned names and places complete the word, matching developments sit under them, results update with every letter; an empty search shows *Populært nu*.

- App: the search field follows the keyboard also while the page is scrolled (iPhone), and the tabs step aside while typing; Android resizes the page for the keyboard. Settings and the owner sheet fit the part of the screen one can see (`--vvh`), so in the browsers inside Messenger or a text message their top is no longer cut off.
- Owner admin: holding the main story offers today's strongest stories to choose from (data.json owner.lead); holding any story offers Opprioriter / Nedprioriter (owner.rank: ±30 on the radar's rank, raised stories go before the editor's picks, lowered ones lose their pick); the quote chooser shows when each statement was said (only there) and lists statements, not headlines; every button in the owner sheet spans it.
- Owner admin: holding the front page's quote opens a chooser (the editor's statements and today's recap lines, or "Automatisk"); the pick is signed, kept by the radar (`removed.json` quote, `data.json` owner.quote) and shown to everyone.
- App: a new front page, organised by story and time: the date and the day in a sentence; **Dagens historie** – the main story as one package: picture with a Danish headline when one exists, "Sådan udviklede det sig" (a timeline from the recap's lead topic), and a statement from the same story; then the 4 other top stories (the main story not repeated), Dagens citat when the package had none, **Lige nu** (the three newest outlet lines, in Danish, with "Se alt i Live"), the sections, the recap and earlier days.

- App: a tap on the logo goes to the top of the front page (holding it still asks for the admin code).
- App: the mark is smoothed where ر meets ب (two small fills, `.ink-fix`): no step under the head of ر, no bump from the tooth of ب, and the bottom edge runs evenly into the line – in the intro, the header logo and the app icons.
- App: the calligraphic mark (خبر in Aref Ruqaa with the red dot) is now the header logo and the app icon (all sizes, maskable and the status-bar badge); the old Lalezar font is gone.
- App: an intro screen in the app's own colours (light or dark from the phone's setting, or the look chosen in Khabar): خبر is written as with a reed pen – a flat nib at 60° (a hairline up the first leg, broad only as it crosses back along the line), in the calligrapher's order (up and round the loop of ح, back through ب into the tail of ر, the dot of ب, then the red dot of خ, which sends out two hairline rings like a quiet signal), in Aref Ruqaa (no Latin name under it). The first visit then says what Khabar is for and waits for "Kom i gang"; later starts show only the 1.5 s writing (a tap skips it).
- App: "N mere fra døgnet" on section pages is a list row with the hidden stories' pictures as small overlapping circles and a chevron ("Vis færre" folds them back).
- App: no text selection or pop-up menu on a long press anywhere (only in the search and code fields); the admin code is entered in a small sheet of its own after holding the logo 1.5 s.
- Radar: the same kind of event in different cities (a protest in Copenhagen, one in London) is no longer one story – `config/places.json` names the cities, and texts naming different ones join only when all but identical (`same_story_other_city`).
- Owner admin: hold the Khabar logo for two seconds and enter the admin code (made by `scripts/setup-admin.ps1`, stored as the ADMIN_KEY secret); then holding a story down removes it (irrelevant, not news, duplicate) or moves it to another section. Signed with the code, so only the owner's phone counts. Removed stories leave the app for everyone at the next run; stories very like an irrelevant one stay out, near ones rank lower (`src/radar/admin.py`, `state/removed.json`), and the editor reads the list at 07/15/21.

- App: the side-by-side pair never changes shape: a tapped card gets a quiet frame and its story (full headline, buttons, coverage) slides open in one panel under both cards.
- Radar: outlet hub pages ("Latin American News | Latest Latin American News") are no longer taken for stories.
- App: "Vigtigst i dag" is now "Døgnets vigtigste" (it holds the last 24 hours); on Danmark, Mellemøsten and Verden only the pictured top stories show, the rest behind "Vis N mere fra døgnet", so the latest news follow right away.
- App: pictures look like press photos – hard contrast, 15 % colour and a fine film grain on the big pictures only, the small thumbnails stay soft black and white (an opened story gets 30 % colour and keeps the grain and contrast); day bands carry a soft tint of the section colour.

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
- Small pictures on every card: the feed's own image, another outlet's picture of the same story or the article
  page's share image, shrunk by the radar to a 144 px JPEG of a few kilobytes (`t/` on the data branch,
  `src/radar/thumbs.py`). Telegram channels never lend a picture, and a site's logo or default picture (one
  picture for several stories) never counts. Where there is none, the outlet's initials.
- Bold keywords: the words in a headline that say who and where – people, parties, places, organisations, and
  the speaker of a 'Who: what' headline – are set in bold (at most three; `Sections.keywords`, sent as `kw`,
  `kw_tr`, `kw_da` for each version of the headline). Colour stays minimal: a small dot for the section on
  mixed lists, red only for a big story and 'live'.
- **Seneste** (fifth tab): everything Khabar picked, newest first, all sections mixed, with the time of day.
- `scripts/editor.py` for the Claude editor: `input` lists the period's stories and every Al Jazeera wire line
  no edition has covered yet; `publish` checks the edition (no wire line may be missing or used twice), adds
  links, sources and the share texts, and writes `digest.json` and `moves.json` to the digest branch.

### Changed

- The editor runs three times a day again (07, 15, 21) and does four jobs: lifts the stories that matter most
  geopolitically (for Danmark: those most useful in the group's dawah) to the top of 'Vigtigst i dag', moves stories
  that landed in the wrong section, chooses statements for quote cards, and adds to the recap; a line goes into the
  day it happened, so at 07 what came before midnight completes yesterday's recap. The phones are told once, at 21.
- Section pages have a shape: one lead story big, two side by side, the compact list, and the editor's quotes in it;
  each section has a quiet colour (Danmark blue, Mellemøsten green, Verden purple). 'Live' is red only while it holds
  stories the reader has not seen there.
- Front page: the day's lead story opens big (its outlet's own picture, headline on a dark veil), the rest are
  compact rows with a small black-and-white square picture; the radar passes on each picture's original (pic).
- Story pictures are cut around the biggest face (OpenCV's face finder, new dependency in the cloud only)
  and shown in black and white in the lists; an opened story shows its picture in colour.
- A story's picture now fills the right of its row and fades into the page instead of sitting in a box;
  the radar makes 360x270 pictures for it. Stories without a picture show no box.
- After a tester found it hard to follow: the recap is one row that folds out; day bands say 'I dag · lørdag
  10. oktober' on a dark label; rows show the clock time ('kl. 14.05', 'i går kl. 22.10') instead of '5 t';
  'Vigtigst i dag' holds today's stories; the selected tab sits on a pill and the tab bar has a clear edge.
- Notifications switch on with one tap: the app sends the phone's push address to the radar through the
  relay, the radar keeps the list encrypted (state/phones.bin, PROFILE_KEY), caps new phones at 30 a day and
  drops phones that switch off or disappear. No more NYHEDSRADAR-PUSH codes to copy and forward.
- 'Stor historie' is now 'Topnyhed' in the app and in notifications.
- One recap a day instead of an overview that grew three times a day: at 21:00 the editor writes 'Resumé'
  (up to 25 short 'Who: what' lines covering the day since 21:00 the evening before), it replaces the previous
  one under 'Vigtigst i dag' (now 8 stories) and the phones are told right away. Owner's request: news on the
  front page that the overview did not have looked odd.
- The overview is now one overview per day at the bottom of the front page, titled with the date ('Overblik
  10. oktober'): the day's most important movements as short 'Who: what' lines in the style of Al Jazeera's
  breaking wire, grouped by topic with the time at the left, newest first. The editor adds to it at 07, 15 and
  22 and the first update after midnight starts a new day; earlier days stay in an archive. The two-to-three
  sentence summaries and the 'Også' row are gone; 'Vigtigst lige nu' opens the front page and no longer hides
  stories the overview mentions. A notification about an update names its most important new line and opens
  the app on the overview; an update that adds nothing sends none.
- Android: icons that a round launcher mask cannot cut (maskable), a one-colour status-bar icon, screenshots and
  shortcuts for Chrome's install window, a neutral app description, and an 'Installer Khabar' offer in the
  settings when Chrome allows it.

- Claude's overview now comes three times a day – 07, 15 and 22 – and each edition covers the stories since
  the previous one (no repeats between the 15 and the 22 edition); 45 editions are kept (about two weeks).
- Default look: **Dæmpet** (soft grey) in light mode and **Notion** in dark mode, listed first in the
  settings; every phone starts there once (an earlier tone choice is reset once), then chooses freely.
- **Overblik and Bevægelser are one edition** (07 and 22), kept compact: one line per topic – its name in bold,
  then the headline, and a small count of statements; tap for the summary, the source (Læs, Del) and 'Det siger
  de' – the Al Jazeera wire lines on it, translated by Claude. Topics with only statements share one line
  ('Også …'). 'Del overblik' shares the stories, 'Del udtalelser' the statements in the group's 'Politiske
  nyheder' format. Earlier editions stay under 'Tidligere overblik' on the front page.
- Front page = the overview, then 'Vigtigst lige nu' (the radar's six strongest stories of the last hours that
  the overview does not already have) and the earlier overviews – no longer one endless mixed list.
- Headings that cannot be confused: a block ('Vigtigst lige nu') is a large title with a red live dot; a day
  ('I dag', 'I går') is a slim band that stays under the top bar while its stories pass.
- Story rows: the headline in plain type with its keywords in bold and one quiet line below ('Stor historie' in
  red, the section, outlet, time); '2 medier' and 'oversat' are no longer in the list (the coverage and the
  translation note are in the opened story).
- Telegram posts in another language than their channel's (Turkish on an English channel) are recognised and
  translated instead of being shown as they are.

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

- The front page no longer repeats the overview's stories when another outlet's article has since become their
  card; shares and opens from the overview teach the radar again.
- Telegram posts: the first line is the headline, links and sign-offs like '[Ak]' are gone, 'No. 9' no longer
  ends a sentence, 'Lebanese/Syrian/local sources' prefixes are dropped; zero-width marks are removed everywhere.
- Share texts skip half sentences, links and sign-offs instead of sending them to WhatsApp.
- Bold keywords: names only (topic words like 'finanslov' and 'regeringen' no longer bold), no column labels or
  hub pages as speakers ('THE LATEST', 'Afghanistan News'), Title Case headlines recognised, whole words only.
- Light news (northern lights, selfies) is never 'big' or 'important'; a section's 'Vigtigst lige nu' shows only
  important stories (the strongest three on a quiet day).
- Unconfirmed Telegram posts fill at most about an eighth of a section; one community source teaches the taste
  profile at most ten stories a day (two channels made two thirds of it).
- 'Strike(s)' in war news is translated as 'angreb', not 'strejke'; Ukrainian places (Zaporizjzja, Kharkiv …)
  place a story in Verden.
- Outlets are shown by name (DR, Politiken, The Guardian) instead of feed names; a source is marked as failing in
  the settings only after three failed runs in a row.
- Tab dots clear once the tab has been visited, and a quick trip to WhatsApp no longer marks everything as seen.
- The app asks the server whether the data changed instead of downloading it all every two minutes; offline it
  says 'Ingen forbindelse'; search finds Erdogan as Erdoğan and is refreshed after 15 minutes.
- Readability: darker grey text (WCAG 4.5:1), 44 pt buttons, 'ubekræftet' in grey instead of orange, VoiceOver no
  longer reads every refresh aloud; coverage lists say how many more outlets carry a story.
- The overview editor uses the time a story was found (a radar gap could hide stories from the next edition);
  a changed setting no longer sends the radar back to downloading its language models.
- From the second day on, the outlets' copies of a story that had left the 36-hour story window came back as
  separate cards (one story could become eight). An outlet's copy now stays part of its story.
- A liveblog or podcast that became a story's lead hid the whole story (four multi-outlet stories, among them
  Al Jazeera's lead, were invisible). Noise no longer joins stories.
- Middle East Eye (compressed feed, frozen since 2019), Jerusalem Post (frozen feed, clock three hours ahead) and
  Jyllands-Posten (Google News returned old articles) now deliver fresh stories; the seven regional TV 2
  stations count as one outlet, so shared stories no longer look like big news.
- 'grundlov' matched 'grundlovsforhør' (custody hearings lifted crime stories into Danish politics); selfies
  count as light news.
- Notifications only for stories an established outlet carries (no single Telegram posts); a notification for a
  story that has since joined another card opens that card instead of nothing.
- The feedback relay is public, so anyone could post fake 'shared' signals with any text: the radar now learns
  only from stories it has, with its own text, at most 40 signals a day.
- A network hiccup when reading the saved state made the radar start empty and overwrite 30 days of learning;
  it now stops instead.
- Machine translation of Arabic got names wrong ("Island correspondent" for Al Jazeera, "Trimpe", "Butin"); a name
  glossary fixes them before and after translating.
- A new Bevægelser briefing now shows even when the overview itself is unchanged.
- A Danish debate piece about Muslims in Denmark (B.T., no country named) landed in Mellemøsten because its nearest
  stories were Middle East stories about Islam. A Danish article about Islam and Muslims, immigration or Danish
  politics that names no other country now always stays in Danmark.
- Wire lines that reached the radar a few minutes before Claude's run but after Claude read the list fell
  between two editions; every edition now records the lines it covered (`ids`), and the next one takes every
  line no edition has covered.
- Unrelated Arabic headlines were merged into false 'big stories' (the language model puts some Arabic texts
  almost on top of each other); Arabic-only stories are no longer merged, and a story's card now comes from an
  established outlet rather than a Telegram post whenever one carries it.

### Removed

- The 'Kopieret' tab, swipe-to-copy, the red 'KOPIERET' stamp, the ink-drop pull-to-refresh, the splash
  animation, the relevance bar and the guessed 'learned' lines (word overlap with earlier copies).
- The 'Blød' tone; the 'Sådan vælger Khabar' section in the settings; every mention of Claude in the app.
- The separate Bevægelser tab (its content is now inside the overview) and the endless mixed list on the front
  page (now the Seneste tab).

---

<!--
Release entries look like this, newest first:

## [1.0.0] - 2026-01-15

### Added
- The thing that is now possible.

### Fixed
- The thing that used to be broken.
-->
