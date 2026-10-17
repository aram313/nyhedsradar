# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

## [Unreleased]

- **A story reached from another page opens on a page of its own, with the way back; an edge drag goes back**
  (2026-10-18, the owner: 'any time you get directed to news … it has to have the temporary page with the back sign
  on top … so i can get right back to where i was redirected from' and 'a drag from screen border from left to right
  should also send you back'; `?v=20261018bm`): a new side page 'Nyhed' (`nyhedPage`, `openStory`; `?item=` in the
  address) shows the one story opened, with Læs, Del, Kopiér and Gem and 'Alle nyheder i Live ›' under it; the bar's
  back mark – and the phone's own back – returns to the page and the place one came from. Every redirect to a story
  goes there when it starts outside Live (`openInLive` from another tab: the front page's Live strip and developments,
  the Kalender's stories, Leksikon, Gemt; Økonomi's stories, also those Live does not hold – the 'Fra Økonomi' block
  in Live is gone); in Live itself a story still opens in place. On a side page, a drag from the screen's left edge
  goes back in the app on an iPhone's home screen (the page follows the finger and slides away; Safari and Android do
  it themselves through the history). No dimming on the Nyhed page: its story is the page.
- **An open story: the page scrolls a little, never away from it** (2026-10-18, the owner: 'now im not even able to
  scroll i should at least be able to scroll a bit to center the story on the screen'; `?v=20261018bl`): the page is
  no longer frozen while a story or an event is open; it scrolls as far as keeps the whole story between the bar and
  the dock, and is held at that edge beyond it (`holdOpen`, from the page's scroll; it waits 450 ms for the app's own
  move into view). Closing still returns to where one was.
- **An open story holds the page still, and closing it returns to where one was** (2026-10-18, the owner: 'når man
  åbner en historie, at man ikke kan scrolle væk fra den, kun i dens område, og når man lukker den igen er man tilbage
  til den position som da man åbnede den'; `?v=20261018bk`): while a story or an event is open the page is locked
  (`.page.locked`: no scroll of its own, no pull to refresh, the wheel goes to the story); what is open fits between
  the bar and the dock and scrolls within itself when it is taller; the page gets room below while locked, so a story
  opened low still comes fully into view. Closing it – by its own headline or a tap outside – puts the page back at
  the position it had when the story was opened (`focusY`).
- **The dimming without a layer, and steady while one scrolls** (2026-10-18, the owner: 'når man folder en historie ud
  nu er den dæmpet et kort sekund' and 'hvis man åbner en historie … og scroller op og ned, kan nogle af de historier der
  er dæmpet blive lyse igen'; `?v=20261018bi`): in the app the rest of the page is no longer covered by a layer – every
  box beside the open story or event takes `.dimmed` (opacity only, as on Økonomi), so nothing ever lies over what is
  open, and the page still scrolls while it is open; a tap outside it is caught on its way down and only closes. The
  fade runs only as something opens (`.fading`, 260 ms): a row drawn later – one that scrolls into view – is dim at
  once instead of fading from light again.
- **One thing open at a time, the rest of the page dimmed; a tap outside only closes** (2026-10-18, the owner: 'når
  noget er åbent på en side … bør resten af siden dæmpes til man lukker den igen … kunne lukkes hvis man trykker uden
  for zonen', 'der er en streng regel med kun én ting bør kunne være åbnet af gangen' and 'hvis man rammer en anden
  historie når man trykker på den dæmpede zone, så burde den historie ikke åbnes, men kun lukke den aktive';
  `?v=20261018bg`):
  - **In the app** an open story or calendar event lifts above a layer that dims the page in view (`focusSync`,
    `.dim` placed right before what is open so the two share one stacking order, `.lift`); a tap on the layer only
    closes (`closeOpen`) – the story under it is not opened; with nothing open the page is free again. Opening a
    story closes every other story (other tabs too) and an opened event, and an event closes a story. The bar and
    the dock are not dimmed.
  - **On Økonomi** a tile, a row under 'Flere tal' or an unfolded story is the one open thing (`sole` closes the
    rest, in any topic); everything around it dims (`.dimmed`, opacity only) and a tap outside it – caught on the
    window first – only closes.
- **Denmark's fuel prices as a chart; 'Finans og økonomi' a week at a time; every tap there into Khabar; A–Å's
  letters centred** (2026-10-18, the owner: 'Der er for mange nyheder på økonomi i dag, lav det så den viser 1 uge af
  gangen … når man trykker på en bør den sende til nyheden i khabar', 'kan vi få grafer på danske benzin og
  dieselpriser som vi har på amerikanske?' and 'de lodrette bogstaver ikke centreret i deres baggrundsboks';
  `?v=20261018bc`):
  - **Denmark's petrol and diesel, two years week by week:** the EU's Weekly Oil Bulletin's whole history (one ~4 MB
    sheet, read daily: `energy.fetch_dkh`, `dk_history` → `energy.json`'s `dkh`, kr. per litre from EUR per 1000 l and
    the week's rate). An opened Danish fuel tile shows it with ranges ('Landsgennemsnit uge for uge, med afgifter') above
    the chains' own daily line as that grows; the tile's sparkline uses it until the daily line has two weeks.
  - **One week at a time:** 'Finans og økonomi' lists the last seven days under its headline, the rest behind
    'Ældre nyheder (N)'.
  - **Into Khabar:** a story Live holds opens there; one it does not (the backward fill) opens in Live too, first and
    opened under 'Fra Økonomi' with Læs, Del, Kopiér and Gem (`outside`, `khabarOpenStory(id, item)`; 'Luk' takes it
    away). Only khabar.nu/energi on its own unfolds it in place.
  - **A–Å's letters** are centred in their track.
- **Økonomi's stories open in Khabar; 'Vigtige datoer' says the month** (2026-10-18, the owner: 'når man åbner dem
  skal det ikke åbne ekstern link med det samme, det skal åbne i nyhedsoversigten i khabar' and 'forsidens vigtige
  datoer kan være misvisende, fordi der står et tal og en ugedag'; `?v=20261018bb`): a story tapped on the economy
  page (its news lists and the headline's line) opens in Live, opened, when Live holds it (`khabarOpenStory`); on
  khabar.nu/energi it opens the app at the story; one Live does not hold (the backward fill, one that left Live)
  unfolds in place with its original headline and 'Læs hos <outlet> ›' – the outlet only when one asks. The front
  page's 'Vigtige datoer' shows the month under the day ('14 dec.') instead of the weekday: it has no month bands
  (the Kalender keeps the weekday). (The 14 stories of 'Finans og økonomi' reached the live page with the radar's
  pass of 22.21; a copy fetched before showed none.)
- **'Finans og økonomi' with a month's memory, a backward fill, its newest story as its headline; pull to refresh on
  Økonomi; no 'Høj betydning' on 'Vigtige datoer'** (2026-10-18, the owner: 'kan vi fylde uro i økonomien i
  retrospekt', 'synes ikke uro i økonomien lyder godt … overskriften … skal være lidt mere professionelt', 'man kan ikke
  hive ned for at opdatere økonomi siden', 'der skal ikke stå "høj betydning" på forsiden'; `?v=20261018ba`):
  - The economy page's news topic is **'Finans og økonomi'** ('Nyheder' in its dock, `#nyheder`); its serif headline
    line is its newest story's headline, with that story's outlet and time under it as the way to it, and the list
    holds the rest (`newsPick`, `newsTidy` shared with the list).
  - **Its own memory:** `energy.crisis_archive` keeps the topic's stories 30 days (the radar's of the last four days
    added at every run to what it held; one story once – its id, its link, or three shared stems within two days),
    at most 40, newest first.
  - **The backward fill** (`config/crisis-seed.json`): 13 stories of 18/9–17/10 found with the scouts' subjects on
    Google News – Frankrigs lånerenter og ECB (Lagarde, Draghi, IMF-chefen, Scope's downgrade, the sell-off near the
    euro crisis's level), IMF and Pakistan, Egypt and China, the EU–China car deal, Trump's Russian diesel, euro-zone
    inflation, the Bank of England's warning – each with a Danish headline in the editor's style.
  - **Pull to refresh on Økonomi:** its page scrolls inside the app's frame, so it has its own pull, as the app's
    pages (the page follows the finger; a deliberate pull fetches the numbers again; embedded, the app's logo answers:
    `khabarOkReady`, `khabarOkRefresh`).
  - **'Vigtige datoer'** rows on the front page no longer say 'Høj betydning' (they all are; the title says it); the
    Kalender keeps the label.
- **'Vigtige datoer' on the front page; 'Uro i økonomien'** (2026-10-18, the owner: 'sker snart har i dag kun 1
  begivenhed … burde tage 3 måneders højt vigtige begivenheder i rækkefølge, maks 4. glem middel vigtighed. og måske en
  anden titel' and 'Måske skal det ikke hedde "økonomiske kriser"'; `?v=20261018az`): the front page's calendar block
  is called 'Vigtige datoer' and holds the events of high weight of the next three months (92 days), in their order,
  at most four (a month alone after its days and without a countdown; a year alone is no date). The economy page's
  topic 'Økonomiske kriser' is 'Uro i økonomien' ('Uro' in its dock, `#uro`): it holds borrowing stress, tariffs,
  sanctions and ratings as well as a crisis proper.
- **Scouts, a wider crisis topic and France's rating days** (2026-10-18, the owner: 'frankrig har spurgt om et
  massivt lån fra ECB, hvordan skal vi inkorporere sådan nogle informationer … og hvorfor er de ikke med i dag' – no
  formal request was found, but the French debt stress was real and none of the radar's 697 stories named it; he chose
  three of four proposals, the editor keeps no internet):
  - **Scouts** (`config/feeds.json`, `"scout": true`): four Google News searches on fixed subjects across outlets –
    states' borrowing stress (bond yields, borrowing costs, ratings, debt crises, bailouts, IMF loans), central banks
    stepping in (ECB, Fed, BoJ), deadlines (ultimatums, votes, summits on Gaza, Iran, Ukraine, tariffs, the Security
    Council) and Danish deadlines (frist, finanslov, afstemning). An item keeps the outlet Google names (`feeds.parse`);
    an outlet that is no source of ours stays off the scale (`run.OffScale`: it may reach Live, at most three cards of
    its own a day, never moves the established sources' scale). Polled with the radar, so they are there within
    minutes, not once a day.
  - **Økonomi → Kriser** (`energy.CRISIS`) also knows bond yields, borrowing costs, the spread to German bonds, the
    ECB and Lagarde, bond-buying, credit outlooks, budget and fiscal crises, lånerenter, renteforskel,
    statsobligationer, kreditvurdering, budgetkrise.
  - **Kalender:** Moody's review of France 23/10, S&P's 27/11 (each of middle weight, checked), France's 2027 budget
    to be adopted in December (forventet; the prime minister's own aim, no fixed day).
- **Sideways chip rows start at their left and fade at their edges; A–Å's letters in a track, once the list begins**
  (2026-10-18, the owner, with a screenshot: 'Ser lidt uprofessionelt ud med alfabetet i højre side, ligner en
  eftertanke. Og den vandrette scrollbare emneliste fader ikke ud i siderne, burde den gøre på alle sider, og burde
  starte på venstre side som standard, i dag starter den på slutningen'; `?v=20261018ay`): the dock's centring of a
  few chips (Kalender, Analyser) is done by auto margins, so a row wider than the screen starts at its left (centring
  had pushed the A–Å's kinds row off its start). Every sideways row (the dock's rows, the A–Å's kinds) fades out at the
  side where more lies beyond (`edges`, a mask toggled by `fade-l` / `fade-r` as it is drawn and scrolled). The A–Å's
  letters sit in a slim rounded track at the right edge, evenly spaced and vertically centred, shown only once the
  list itself is reached (`azWatch`: not beside the header and 'Mest brugt'), fading in and out; the rows keep 40 px
  clear of it.
- **Dagens historie's picture smaller** (2026-10-18, the owner: 'dagens historie billede er for stort';
  `?v=20261018ax`): 16:9 instead of 4:3 and at most 40 % of the screen instead of 62 % – about a quarter lower on a phone
  (≈ 230 px at 430 px wide); a four-line headline and its line still fit on the fade.
- **The front page's 'Det sker snart' only of high and middle weight** (2026-10-18, the owner: 'forsidens "sker snart"
  burde kun have middel og høj betydning'; `?v=20261018aw`): the block's next three or four events of the coming 14
  days leave out what is of low weight (`calWOf(e) > 1`); with none of weight in the fortnight there is no block.
- **'Leksikon', and a Svar · Leksikon toggle; search words underlined in red** (2026-10-18, the owner: 'Burde begreber
  a-å ikke hedde måske opslagsværk og være lidt mere fremtrædende?' – he chose 'Leksikon' and the toggle – and 'når man
  søger burde ordet … være markeret med en rød [under]stregning, i dag er den grå'; `?v=20261018av`): Analyser's dock is
  one toggle of two chips, Svar · Leksikon, shown on the answers' list and on the Leksikon A–Å alike (Leksikon opens the
  A–Å as a side page, Svar goes back to the list; the toggle does not fade between them). The wiki is called Leksikon
  wherever the app named it Begreber: the bar's title, the A–Å's header ('Leksikon A–Å · 203 opslag'), search's scope
  and group, Gemt's group, an answer's 'I leksikonet', the intro; the A–Å's kind 'Begreber' (the concept pages) stays.
  A search word is bold with a 2 px red underline instead of a grey tint.
- **Økonomi: the whole topic block lights up** (2026-10-18, the owner: 'det skal være hele blocken der lyser op'): the
  soft ground behind a topic tapped in the dock now covers its whole block, from just above its red rule to its foot,
  behind its tiles and rows (`.ec-sec::after`), not only its title.
- **Analyser's dock: only 'Begreber A–Å'** (2026-10-18, the owner: 'Under analyser, skal der ikke være filter i bunden.
  Kun en Begreber knap'; `?v=20261018at`): the areas and the years are gone from the dock; the one chip sits in its
  middle and opens the A–Å index. The search field under the bar still finds an answer; the list keeps its year bands.
- **The Kalender's toggle as Live's chips; Økonomi's topic lights up** (2026-10-18, the owner: 'Vigtige / Alle er nu en
  grå boks der ikke er centreret … vigtige knappen stadig kan have en rød accent … følge stilen som resten af siderne,
  f.eks på live' and 'når man trykker på en kategori i økonomi, skal baggrunden på kategorien lige lyse lidt op';
  `?v=20261018as`): the toggle is two chips in the middle of the dock, 'Vigtige' with the weights' short red edge, the
  chosen one a step lighter as everywhere. On the economy page a topic tapped in the dock – the app's or its own – has
  its top on a soft ground that fades out (1.6 s, only opacity; under Reduce Motion it shows and goes without a fade)
  once the page stands still there (`flashTopic`).
- **The Kalender's dock is one toggle: Vigtige · Alle** (2026-10-18, the owner: 'filter kun være "Vigtige" og "alle"
  og det skal være en toggle'; `?v=20261018ar`): a two-part segment replaces 'Kun vigtige' and the kinds' chips (Valg,
  Topmøder, Centralbanker, Frister, Danmark); the kind still shows by its dot on each row. The choice is remembered;
  the page's 'skjult' line is gone in the Kalender (the toggle says it). Live keeps its chip.
- **No flash of the stand-in faces on a reload** (2026-10-18, the owner: on F5 'gamle logo, gamle overskrift
  skrifttype' for a split second; `?v=20261018aq`): the two Google font sheets (the mark's Aref Ruqaa, the headline's
  Source Serif 4) are read before the first paint instead of after it (they were loaded with the `media="print"`
  trick); the service worker already keeps the sheets and files on the phone, so on a reload they are there in a few
  milliseconds. The mark keeps `display=block`, the headline face takes `display=fallback` (it shows when it arrives
  within a tenth of a second, else the stand-in stays for that visit, never a late swap).
- **A fuller calendar** (2026-10-18, the owner: 'kalenderen ser lidt tom ud, kunne der være noget vi har overset?'; he
  chose all four proposals; `?v=20261018ap`): about twice as many events of high or middle weight (20 → 39).
  - **Elections:** Wikipedia's 'Unknown date' elections of weight are kept as the year alone ('i løbet af 2027' –
    Italien, Polen, Tunesien, Libyen, Bahrain, Emiraterne, Grækenland, Slovenien, Tadsjikistan); India's Council of
    States and an undated election the page also dates are left out. Wikipedia has no 2028 page yet, so 2028's
    elections of weight are curated: Tyrkiet (senest 14/5-2028), Iran (præsidentvalg, juni 2028, forventet), Malaysia
    (senest februar 2028).
  - **Fixed deadlines, each with its checked source:** the US–China trade truce ends 10/1-2027 (extended in September
    from 10/11), UNIFIL ends 31/12-2026, a new UN Secretary-General takes office 1/1-2027, Denmark's seat in the
    Security Council ends 31/12-2026.
  - **Recurring meetings:** IAEA's Board of Governors (Iran's nuclear file; November 2026, March and June 2027), NATO
    2027 in Tirana, and the annual BRICS, SCO and Arab League summits of 2027 (the year alone where no date is out).
  - **The app** shows a year alone as 'i løbet af 2027' in a band after its December ('Senere i 2027 · dato ikke
    fastsat'); a curated event may set its weight (`w`).
  - **The editor** gets 'Dates in the news' in its input: the stories of the last two days that name a coming day or a
    deadline, each with what the calendar holds then, to decide on every one (routine prompt updated).
- **Middle weight in a darker red; rate decisions quiet** (2026-10-18, the owner: 'den røde streg ved middel betydning
  [lidt mørkere] … og den burde fjernes på kalenderens rentebeslutninger, da det er abstrakt'; `?v=20261018ao`): the
  middle weight's edge in Live and the Kalender takes `--red-deep` (#7e2a26 light, #a8403c dark), the high one keeps
  `--red`; every central bank's rate decision is of low weight (`calendar.weight`, and the app's `calWOf` at once).
- **'Kun vigtige' in Live and the Kalender; the Kalender shows everything** (2026-10-18, the owner: 'en knap der
  frasorterer alt med lav betydning på kalender og nyheder. kalender skal ikke have en sortering med måneder, men skal
  som standard vise "alt"'; `?v=20261018an`): a chip 'Kun vigtige' (with a short red edge, the weights' sign) first in
  each dock hides what is of low weight; it is remembered on the phone (`liveImp`, `calImp`), and the page says at its
  top what it hides ('Kun høj og middel betydning · 18 skjult') with 'Vis alt'. A story or event of low weight opened
  from elsewhere shows the whole list again. The Kalender's 3 mdr · 12 mdr · Alt is gone: everything ahead is shown,
  still under its month headers.
- **Middle weight: the red edge without the ground** (2026-10-18, the owner: 'en rød streg på samme måde som stor
  betydning men bare uden den røde baggrund'; `?v=20261018al`): in Live and in the Kalender a story or event of middle
  weight has the high one's 3 px red edge at its left, without the soft red ground; the short mark under the time (the
  day, in Kalender) is gone.
- **No more ochre ground: the movement's text is marked by a thin warm rule** (2026-10-18, the owner: 'den gule
  baggrund skal genovervejes, det gør det svært at læse'; `?v=20261018ak`): Hizb ut-Tahrir's blocks (an answer's panel
  and text, a wiki page's lead, readings and timeline, the answer line under a story) stand on the page's own ground in
  the page's own text colours, in the serif, with a 2 px warm rule at their left (`--ht-rule`, #a8884f light, #9a8256
  dark) and their one label; the wiki chips take the ordinary chip ground.
- **'Læs hele svaret (engelsk)' clearer, still quiet** (2026-10-18, the owner: 'mere tydelig, dog … ikke stor og
  klodset'; `?v=20261018aj`): one hairline-framed row (radius 12, 44 px) with a small book, the words in the text's
  colour and a chevron that points down while folded and up when open.
- **The ochre tint dimmed again** (2026-10-18, the owner: 'må stadig gerne dæmpes lidt mere'; `?v=20261018ai`): light
  #f0ebe1 → #f0ede6, dark #24211c → #22201c (its hairline with it); the movement's text keeps its contrast.
- **Side pages keep the column on a desktop** (2026-10-18, the owner: A–Å, a wiki page and an answer ran 'fra border til
  border'; `?v=20261018ah`): a side page is fixed to the window, so it now takes the tabs' 680 px column, centred
  (A–Å, a wiki page, an answer, Gemt, Udvikling).
- **A–Å's letters quieter, at the edge, and right going up** (2026-10-18, the owner: 'mere diskret … virker ikke når
  man scroller op … ligger den midt på siden på desktop'; `?v=20261018ag`): the letters are small and grey at the
  window's right edge (not the column's, which sat mid-screen on a desktop); a jump aims at a zero-height mark before
  each letter band (`.az-at`) – a band that sticks under the bar reports where it sticks, so jumps upwards missed.
- **'Høj betydning' weighs the editor and the books above the coverage** (2026-10-18, the owner approved the review
  and added: 'stor dækning burde vægte mindre end redaktørens valg eller bøgernes tungeste katagorier';
  `?v=20261018af`): at most five stories at a time by points – the editor's first three picks (or the owner's raise) 4,
  another pick 3, the books' heaviest tiers (1–4, and 6: Danish policy on Islam and Muslims) 2, a big story by coverage
  1; two points are needed, so coverage alone no longer makes a story high, and a tier without the editor needs a
  confirmed story. A pick holds it 24 hours, the rest twelve, counted from publication – no more reset at midnight.
  The app (`topScore`, `topNow`) and the radar's notifications (`run.top_score`, `top_now`) are the same; Live's middle
  weight is an editor's pick, a heaviest tier or a big story. The editor's prompt (the routine and
  docs/hjerne/routine-prompt.md) says its first three picks are marked 'Høj betydning'.
- **A–Å as the iPhone's contacts, a quieter ochre and red section headings** (2026-10-18, the owner; `?v=20261018ae`):
  the A–Å index's letters are a thin still column at the right (`.az-idx`) instead of a sideways strip: a press jumps
  to the letter, a finger slid runs through them at once, and a large letter in the middle fades half a second after
  the last change (`azGo`); the letter bands stay under the bar in red. The movement's ochre tint is dimmed (light
  #efe7d6 → #f0ebe1, dark #2a251d → #24211c; contrast kept). A wiki page's and the answer reader's section headings are
  red with more room above ('bedre opdeling … overskrifter skrives med rødt').
- **Live is one list that shows each story's weight; 'Topnyhed' is 'Høj betydning'** (2026-10-18, the owner: 'Nyheder
  skal have én fane, ingen "seneste" og "vigtigste" men … fremhæve dem med høj betydning medium og lav som vi har gjort
  på kalenderen' and 'måske topnyhed termet burde ændres til høj betydning'; `?v=20261018ad`): Seneste/Vigtigste is
  gone – Live is everything as it comes in, newest first, with the three section filters in the dock. A row's weight
  (`weightOf`) is shown as the calendar's: high – the day's five strongest big stories, as 'Topnyhed' was – on a soft
  red ground with a red edge and 'Høj betydning'; middle – a big story, an editor's pick or one of the books' two
  heaviest tiers (about a quarter of a day) – a short red mark under its time; the rest quiet. The term is 'Høj
  betydning' everywhere: rows, 'Mens du var væk', the notification switch and the notifications' title.
- **Økonomi's topics in the app's dock, and three small fixes** (2026-10-18, the owner; `?v=20261018ab`): after
  'Råvarer' on a phone the economy page's own dock (fixed inside the frame) could not be tapped until one scrolled up –
  the topics are now chips in the app's dock above the tabs (`okOpts`, `khabarOk`, the frame's `okJump`), the frame
  holds no fixed element when embedded, and a jump never asks for more than the page holds. On a wide screen the wheel
  beside the column now scrolls Økonomi too (its page is in a frame). Gemt's 'Del eller flyt dine gemte' has Del and
  'Kopiér link'. A list's large picture no longer turns grey when pressed: it darkens a little.
- **Gemt to another phone, or to someone else** (2026-10-18, the owner chose 'Flyt-link' and asked for 'tilføj til
  eksisterende bogmærker' or 'erstat eksisterende bogmærker' when the link is opened; `?v=20261018z`): Gemt's foot has
  'Del eller flyt dine gemte' – a link (`?gemt=1#flyt=…`) holding the saves, deflated, in its fragment, which never
  reaches a server (a story keeps headline, outlet, time, link and section; its summary stays behind). Opened, the
  address loses the fragment at once and a sheet asks 'Tilføj til mine gemte' or 'Erstat mine N gemte'; a phone with
  nothing saved takes them at once. Also the way from Safari to the home screen's app on an iPhone (their storage is
  apart). No account, no id, nothing sent.
- **Gemt made calm, and saves that outlive updates** (2026-10-18, the owner: 'Ser lidt uprofessionelt ud, analyser bør
  også være over nyheder (kald det ikke historier)' and 'hvordan kan vi sørge for en bruger aldrig mister sine gemte
  bookmarks?'; `?v=20261018y`): the page lists Analyser first, then Nyheder, then Begreber; every row is the Analyser
  list's row with ONE filled bookmark at the right (the answers had two); a saved story is a quiet row – the headline
  Live shows (in Danish, “israel” in the house style), two lines of its summary, outlet and time – that opens it in Live,
  or the outlet's article once it has left Live; no Læs/Del buttons. A snapshot now keeps the headline the reader saw.
  The list is read leniently (an unusable entry is skipped, never the whole list), a second copy (`saved-bak`) stands in
  when the first cannot be read, and the phone is asked to keep the app's storage (`navigator.storage.persist`, silent
  in Safari and Chrome; not asked in Firefox, which would prompt).
- **Gem on Live's rows** (2026-10-17, the owner: 'gør det samme for "Live" oversigten'; `?v=20261018x`): every row of
  Live (Seneste and Vigtigste) has the bookmark at its right, beside the row's button, filled when the story is saved;
  the row's and the opened story's bookmarks change together.

- **Gem on the answers' list** (2026-10-17, the owner: 'tilføj en "gem" knap til højre på listen over analyser, så man
  ikke skal trykke sig ind på dem og så man kan se hvilke man har gemt'; `?v=20261018w`): every answer row has a
  bookmark at its right, beside the link (never inside it), filled when the answer is saved; it changes at once.

- **The front page in a fixed order, Denmark only when very big, the economy's crises** (2026-10-17, the owner: 'hvorfor
  er citat i bunden på forside, synes godt tingene kunne sorteres bedre', 'kun kæmpe nyheder skal ramme forsiden for
  danmark', 'der skal også være økonomi nyheder, primært kriser … er den stor nok må den gerne tages med på
  forsiden'; `?v=20261018v`): the app draws the editor's blocks in one order – Dagens historie, the day's quote under
  it, the lists in the editor's order, the answer, a line, 'Det sker snart', the developments, Live – and the fixed
  page the same; a Danish list reaches the front page only with a big story among the day's five strongest. The
  economy page has a topic 'Økonomiske kriser' after 'Lige nu' (defaults, debt crises, currencies, bank runs, crashes,
  IMF rescues, sanctions, tariffs; `energy.CRISIS`, the editor's headlines or Danish outlets' own); the editor gives a
  big crisis a pick or a block 'Økonomi'.

- **Brændstof: USA in dollars a gallon, no chains' table** (2026-10-17, the owner: 'USA benzin og diesel pris skal stå
  der og det skal angives i dollars pr gallon', 'flere tal med kæderne er ligegyldigt info'): the four tiles are petrol
  and diesel in Denmark (the cheapest chain, kr. per litre) and petrol and diesel in the USA (the weekly average, $ per
  gallon, the litre price in kroner on tap); the chains' table and the USA group left 'Flere tal', which keeps the raw
  product's share and Europe.

- **The economy page as one long page that changes topic as you scroll** (2026-10-17, the owner: 'økonomi siden kan
  virke lidt uoverskuelig … scroll ned og den skifter i mellem forskellige emner med tydeligt emneskift'):
  `public/energi/` is no longer six tab views with chips but seven topics in a fixed order – Lige nu, Brændstof, Olie
  og gas, Markeder, AI, Gæld, Råvarer. Each starts with generous space, a short red rule, the red fly title and one
  serif headline line made from the numbers ('Brent steg 3,7 % fredag', 'Benzin 17,69 kr. – diesel 18,89 kr.',
  'USA’s gæld: 40,4 billioner $'). The dock at the bottom follows the scroll (IntersectionObserver; the chosen chip
  scrolls into view inside the dock with large text) and a tap jumps to the topic (smooth unless Reduce Motion). Each
  topic shows three or four figures as large tiles – name, value, the move with an arrow, a sparkline; a tap opens its
  chart and the three texts under its row – and one quiet 'Flere tal' row unfolds the rest in place (crack spreads, the
  forward curve, physical minus paper, the products and gas, the other AI stocks and the bubble's points, the chains'
  table with premium and HVO, the EU table, the IMF lands beyond the top five, the energy news). Lige nu keeps only the
  four biggest moves against each figure's typical day (at most two from a topic), each a way to its figure. Time and
  sources are said once, in one line at each topic's foot; a figure says its own time only when it differs (TTF's
  Thursday close, Bitcoin's live price, the weekly US and EU prices). Nothing is opened from an earlier visit, so no
  chart is drawn until a figure is tapped. At 430 px a topic's first view went from Brændstof 1 658, Olie 462, Markeder
  543, AI 1 694, Gæld 1 243, Råvarer 374 px (5 974 in six separate views) to Lige nu 377, Brændstof 461, Olie 509,
  Markeder 509, AI 509, Gæld 645, Råvarer 449 px (3 459 for all seven on one page). No change to energy.json or the app.
- **A fuller explanation for the calendar's weighty events** (2026-10-17, the owner: 'de ting i kalenderen med høj og
  middel betydning må gerne få en lidt mere uddybende forklaring'): `config/calendar-why.json` holds two or three
  sentences of reality for each kind – the elections in the USA (midterms, president), “israel”, Denmark, France,
  Russia, Turkey, Iran, Egypt, Pakistan, Iraq, Syria, Palestine, Ukraine, India, Britain, Germany, Morocco, Nigeria,
  Kyrgyzstan, Oman and the rest of the Muslim world, the Fed, G20, the UN's general debate, NATO, BRICS, OPEC+, the EU
  summits, G7, the SCO, the Arab League and the OIC: what is decided, who takes part and what the outcome governs.

- **The English texts matched by address** (2026-10-17): an answer is matched to its texts by its source page's url (as
  `build_movement.py` numbers the answers), no longer by its number alone – the Arabic and the English sites number
  their pages each in their own way, so eight answers had another answer's text. 318 of 321 now have their own English
  text: 274 from the English editions, 44 translated from their Arabic (each translation names the Arabic file it came
  from, `src`, and is kept only while that is the answer's own); since the same day all 321 – the last three, Sri Lanka, Central Asia and Yemen 27/9/2026, translated too.

- **Vigtigste runs as time runs** (2026-10-17, the owner: 'det er forvirrende at "vigtigste" nyheder ikke er
  kronologiske'; `?v=20261018u`): the day's 30 most important stories (the editor's picks, then the radar's strongest;
  'Vis flere vigtige' takes 60) are shown newest first with Seneste's time column and day rows – the two views differ
  in what they hold, never in their order.

- **EU summits weigh in the middle** (2026-10-17, the owner agreed): what they decide binds Denmark and settles the
  sanctions on Russia, the money for Ukraine and the trade with “israel”, so they carry the middle mark; the editor
  raises one to high weight when its agenda holds such a decision (the routine's prompt says how).

- **The whole answer in English** (2026-10-17, the owner: 'kan vi få hele teksten fra analyser ind på side? … på
  engelsk', the texts published as they are; `?v=20261018t`): every answer the HT archive has in English (272 of 321)
  has its whole text in `public/viden/svar-en/`, fetched when the reader unfolds 'Læs hele svaret (engelsk)'; the
  answers only in Arabic follow, translated ('oversat fra arabisk').

- **The calendar weighs its events** (2026-10-17, the owner: 'vægte de begivenheder på kalenderen der har højeste
  betydning med en indikator eller en baggrundsfarve'; `?v=20261018s`): `calendar.weight` gives every event 3, 2 or 1 –
  3 the elections in the great powers and the states at the centre of the Muslim world, Denmark's general election, the
  summits where the powers meet (G20, NATO, BRICS, the UN); 2 the other elections in the Muslim world, the Fed, OPEC+,
  the G7, the SCO, the Arab League and the OIC; 1 the rest (climate summits, ceremonial presidents) – and the editor may
  give his own entries a `weight`. In the tab an event of weight 3 stands on a soft red ground with a red edge and
  'Høj betydning', one of weight 2 has a short red mark under its day.

- **Kalender instead of the map** (2026-10-17, the owner: "Du skal kassere kortvisningen, eller gemme den … Så synes jeg
  godt, vi kunne have en kalender i stedet for den … Og den skal have en fane for sig selv"; the Islamic dates left out at
  his wish the same day; `?v=20261018r`).
  - The tabs are Forside · Live · Kalender · Økonomi · Analyser. The map is shelved, not deleted: its tab and page are
    gone, its code in app.js, `src/radar/osint.py`, `config/map-places.json` and their tests stay but nothing reaches
    them, so no request goes to Leaflet, MapLibre or the tile servers; radar.yml's Map step is switched off
    (`if: false`); `?tab=kort` opens Forside. The 15 sources added for the map stay (they feed Live).
  - New `src/radar/calendar.py` (stdlib, a radar.yml step after the energy step) writes `calendar.json` on the data
    branch: elections from Wikipedia's national electoral calendars (this year and the next two, the countries of weight
    to the group), the Fed's and the ECB's rate decisions, and the curated summits and fixed dates of
    `config/calendar.json`, each with its checked source. Each source has its own daily clock and keeps its last good
    items when it fails.
  - The editor's own planned events from the news: `editor.py publish` takes an optional `calendar` list (checked like
    headlines, never a forecast – `voice.check_forecast`), kept in `kalender.json` on the digest branch until two days
    after the day; the input lists the calendar's next 30 days; the routine prompt has a `calendar` bullet.
  - The Kalender tab: a red fly title and a serif line naming what comes next, 'Det sker snart' (seven days with their
    countdown), month by month, 'Tidligere' (30 days); rows with the day large, the kind's calm dot (red only for the
    next 48 hours), the place and 'forventet'; a tap shows why it matters, the source, Del · Kopiér and the stories in
    Live that name it. The dock: Alle · Valg · Topmøder · Centralbanker · Frister · Danmark and 3 mdr · 12 mdr · Alt.
    The front page shows 'Det sker snart' (the next three or four events of 14 days) after its second block. An event
    is shared as '17/10 · Midtvejsvalg i USA – … – via khabar.nu/?kalender=<id>', and `?kalender=<id>` opens it.
  - Tests: tests/test_calendar.py (parsing on excerpts of the real pages, the run's clocks, the editor's entries, the tab,
    the dock, the front page block, the share); tests/test_app_kort.py now checks that the map is shelved and loads nothing.

- **A map of more countries, clean when zoomed out, zones to fly to; Økonomi as the fifth tab; the options at the
  thumb** (2026-10-18, the owner: 'der er sket meget mere i ukraine', 'flere forskellige lande, små hændelser', 'når man
  zoomer ud … alt bliver til en stor cirkelring', 'hvis man trykker på de forskellige zoner, så … flyver til forskellige
  steder', 'lav det til en femte fane', 'man kan ikke nå det med tommelfingeren'; `?v=20261018q`).
  - The radar's map keeps a story one established outlet reports alone (never an unverified channel's, a government's
    or the movement's lone post), places 'Russia attacks Ukraine's energy grid' in Ukraine, merges the same place,
    kind and three hours into one event (the outlets summed), and knows about 350 more places (653): Ukraine's front towns
    and oblasts, Russia's struck cities and the Kerch bridge, Sudan, the Sahel, Somalia, Syria, southern Lebanon's
    villages, the West Bank's villages and camps, Gaza's neighbourhoods, Myanmar, Pakistan, Afghanistan, Iraq, Yemen.
  - 15 new sources for the places the radar missed: Ukrinform, Ukrainska Pravda, Kyiv Post, Meduza, The Moscow Times,
    Novaya Gazeta Europe, Sudan Tribune, Hiiraan Online, Libya Review, North Press, LBCI, Kurdistan24, Myanmar Now, DVB
    and TOLOnews (all added for their camp: they never move the established sources' scale).
  - Kort: events close together are one quiet numbered bubble (Leaflet.markercluster 1.5.3, fetched with the map, with
    SRI), a red ring only with an event of the last hour; a tap zooms in or fans them out. Zone chips with counts fly
    the map to Gaza, Vestbredden, Libanon/Syrien, Irak/Iran, Jemen/Rødehavet, Ukraine/Rusland, Afrika or Hele kortet and
    keep the list to the zone. The map stays in view while the list scrolls under it.
  - Økonomi is the fifth tab (Forside · Live · Kort · Økonomi · Analyser) with the economy page filling it; the oil row
    of a story, Indstillinger's 'Mere' and `?tab=priser` (kept as an alias of `?tab=okonomi`) open it. Kort is the map
    only.
  - One options dock above the tab bar on Live (Seneste/Vigtigste and the three filters), Kort (zones, window, kinds)
    and Analyser (its chip row); the top bar keeps only Gemt, search and settings. It goes while the keyboard is up, and
    an opened story's buttons come up above it.
- **The economy page** (2026-10-17, the owner: 'lav det til en femte fane med olie, diesel og benzinpriser … generelle
  geopolitiske tal man skal holde øje med og hvorfor … s&p 500 … landes gæld … AI boblen … interaktiv … live'): the
  energy page (khabar.nu/energi, `energi/?embed=1` in the app's Økonomi tab) became Økonomi with six sections in a
  dock at the bottom – Brændstof (Danish pump prices large, the US weekly average per gallon and in kr. per litre, the
  EU's Weekly Oil Bulletin, the share that is the raw product), Olie og gas, Markeder (S&P 500, Nasdaq 100, Euro Stoxx
  50, C25, Nikkei, Shanghai, the VIX, the US 10-year yield, the dollar), AI (the giants' weight in the S&P 500 from
  SPY's holdings, the basket against the index, why people speak of a bubble), Gæld (the US debt ticking as a labelled
  estimate between the Treasury's daily figures, 16 lands' debt in % of GDP from the IMF) and Råvarer (gold, copper,
  wheat, Bitcoin). Every figure opens a chart and says what it is, why to watch it now and what a rise or a fall
  means; a red fly title and a serif headline line in the manner of The Economist; 'information, ikke
  investeringsrådgivning'. `energy.py` reads the new keyless sources on their own clocks (the slow ones side by
  side) and Henry Hub's physical price works again (EIA's static page).

- **Fresh first, Live's filters, the day under Vigtigste** (2026-10-17, the owner: 'Hvordan kan en frisk historie blive
  gemt under vis flere ift en der er over 24 timer gammel?', '3 nemme filtre … verden mellemøsten og danmark', 'under
  vigtigste skal man også kunne se dato og tid'; `?v=20261018p`): a front-page list keeps the editor's order but puts
  the stories of the last 24 hours before older ones, so none waits under 'Alle'; Live has three chips under its sort –
  Danmark · Mellemøsten · Verden, one tap one section, again all (for the visit only); 'Vigtigste' says the day and the
  time on every row ('16/10 kl. 21.35').

- **The front page's headline in the manner of The Economist, colour on the icons** (2026-10-17, the owner: 'Overskriften
  må gerne være mere fangende, pænere skrift', 'Det skal være mere elegant', 'Se til the Economist for inspiration',
  'lidt farve på ikonerne'; `?v=20261018o`): the date a small red fly title, the lede's first part a bold newspaper serif
  headline (Source Serif 4), the rest its rubric beneath in the same face, a short red rule over each block title,
  Dagens historie's headline in the same serif; the chosen tab's icon red; on the map every kind of event its own quiet
  colour on marker, row and chip.

- **A livelier front page and two looks** (2026-10-17, the owner: 'Forsiden bliver for monoton, brug gerne lidt rød og
  flere nuancer' and 'Skær farvetemaet med til to, de primære mørk og lys'; `?v=20261018j`). On the front page red shows
  where to look: the day's date, a small bar before every block's title, the newest step of a development and its time,
  the ways on ('Alle ›', 'Hele udviklingen ›') and the day's quote (a red tint, a large »); the developments' panel is a
  step deeper than Dagens historie's. `--red` is each palette's red at a strength text reads in (≥ 4.5:1 on page and
  panel). The appearance settings keep only Automatisk · Lys · Mørk: Dæmpet and Notion are the only palettes, and a
  phone that chose another returns to them once.

- **Energy news readable** (2026-10-17, the owner's screenshot: 'Der er noget galt med teksten her'): a row grows with
  its headline (a fixed height let the line under a three-line headline run into the next row), and the news are only
  stories with the editor's headline or a Danish outlet's own – the machine's Danish of a foreign headline read badly
  ('eksploderer … diesel deal', "USA' s") – each story once.

- **“israel” in every Danish headline the app shows** (2026-10-17, the owner: 'må gerne rette de resterende'):
  `quoteIsrael` in app.js (= `voice.quote_israel`) writes the outlets' Danish headlines and teasers and the machine's
  translations in the house style, the map's events and the energy page's news too; the outlet's original headline in
  the credit line and Hizb ut-Tahrir's texts are quoted as they are.

- **“israel” in the editor's text, and the towns of Palestine under their old names on the map** (2026-10-17, the
  owner: 'israel altid skal skrives med anførselstegn “israel”', also 'israelsk'; 'Til byerne skal du bruge de originale
  navne før besættelsen'). `voice.quote_israel` writes every form of the name in lower case inside curly quotes, and
  `editor.py publish` applies it to the draft, the stored files it merges and every file it writes (ids and links
  untouched), so old recap topics keep matching; the routine's prompt says so. The map's labels and its events name
  Yafa, al-Quds, Umm al-Rashrash, Asqalan, Isdud, Bir al-Sab', al-Khalisa, al-Jawlan, al-Naqab and the rest.

- **The map writes its own names** (2026-10-17, the owner: 'Kan du fjerne navnet israel på kortet'; `?v=20261018f`):
  the ground is OpenFreeMap's vector map (OpenStreetMap's data, free, no key) drawn by MapLibre 5.6.0 inside Leaflet,
  every label in Danish where OpenStreetMap has a Danish name, else English, and Israel's name never shown. Without WebGL
  or when the files do not come, the German OpenStreetMap server's pictures stand in.

- **Dagens historie's picture in the press style** (2026-10-17, the owner: 'på den stilede måde med tekst på og en
  mørkere fade i bunden … de 15-30 % med grain'; `?v=20261018e`): the headline and its line in white on a dark fade at
  the bottom of the picture, the app's press photo look (15 % colour, 30 % opened) with film grain; the map's tiles name
  places in Latin letters (OpenStreetMap's German server).

- **A calmer answer reader** (2026-10-17, the owner on the as-Suwayda answer: 'uoverskuelig'; `?v=20261017z`): one
  ochre panel instead of five boxes. The question sits under the title as plain serif text; Del · Kopiér · Gem are one
  row of small quiet buttons (the wiki page's too); 'Svaret kort' and the answer's readings share the panel, each
  reading under a hairline with its subject in bold, no 'Hvad svaret læser' heading; the newest answer on the subject is
  one quiet row under it; 'Begreber' shows four chips before '+ N'; the big 'Åbn originalen' button is gone (the
  byline's 'Originalen' is the way there) and a held English text folds behind 'Læs hele svaret'. Every piece of
  information stays; the as-Suwayda page is 15 % shorter (1,872 → 1,597 px at 430 wide), with one panel where there were
  five boxes and three small buttons where there were three full-width ones.
- **The front page reworked** (2026-10-17, the owner: 'øverste titel skal linke til de forskellige nyheder', 'danmark er
  ikke så vigtig', 'Kan dagens historie ikke få et billede?'; `?v=20261017y`). Each part of the lede opens the story it
  is about – in place when the front page shows it, else in Live – under a thin quiet line, without the wiki's dotted
  underlines; the editor may name the stories itself (`lede_ids` in `editor.py publish`, checked like the picks, kept
  with a kept lede). Dagens historie shows its story's own picture large above the headline (a failed one leaves the
  text lead). Less on the page: at most six blocks, three stories a list (the rest behind 'Alle ›', unfolded in place),
  two updates of the main story's development and 'Hele udviklingen ›', one more story under it, three developments.
  Denmark only when it matters: a Danish list with no big story, no Danish politics on Islam and Muslims and none of the
  day's five strongest is cut to two rows and set last; the fixed page shows 'Danmark' (two rows) only then, and the
  editor's prompt and brain pick Danish stories only when they are important. Live's Danish rules are unchanged. Also
  fixed: a story opened in Live from elsewhere (a timeline step, the Live strip) now really opens there.
- **The Kort tab** (2026-10-17, the owner: 'i stedet for et link til benzinpriser, få en fane for sig selv der bliver
  en slags live osint med kort og seneste angreb lidt ligesom LiveUAmap'; `?v=20261017x`): the tabs are Forside · Live
  · Kort · Analyser. Kort has two views under one segment (remembered per phone): **Kort** – map.json's events on a
  map (Leaflet 1.9.4 from cdnjs, fetched only when the map is first needed; light or dark tiles with the app's look),
  6 timer · 24 timer · 3 døgn (24 by default, remembered), a count line, the kinds as a quiet filter for the visit, the
  events as rows (glyph, place, headline, outlet, time, 'N medier', 'omtrentlig placering'); a row flies the map to its
  event (no flight with Reduce Motion), a marker marks its row and shows a small card with 'Læs' and 'Åbn historien'
  (the story in Live, as a `?item=` link opens it). Markers are the kind's glyph in the text colour on the panel colour,
  a dashed ring when only the country is known, a red ring for the last hour; markers on one another fan out. A drag
  on the map pans the map, never the tabs. **Priser** – the energy page in a frame (`energi/?embed=1`: no bar or back
  link of its own, the app's look and text size followed live). The front page's foot link to the prices is gone; an
  oil story's row and Indstillinger's 'Mere' open Priser; `?tab=kort` and `?tab=priser` open the tab. map.json follows
  the news's reload cycle once the tab was seen, and an unchanged file draws nothing. CARTO's tiles need a free key
  since September 2026: `pages.yml` writes `cartoKey` from the repository variable `CARTO_KEY`; without it the map uses
  OpenStreetMap's own tiles, greyed. The energy page now reads the app's text size (`textSize`). Tests:
  `tests/test_app_kort.py`.

- **The map's events** (2026-10-17, the owner: 'en slags live osint med kort og seneste angreb lidt ligesom LiveUAmap'):
  `src/radar/osint.py` writes `map.json` after every radar pass (a step in radar.yml): the attacks and armed events of
  the last 72 hours in the stories Live shows, confirmed or big, with the editor's headline, placed by
  `config/map-places.json` (about 300 cities, camps, seas and countries; the most specific place wins, a country alone
  is marked approximate), each with its kind (luftangreb, drone, missil, artilleri, eksplosion, til søs, kampe,
  angreb). Threats, plans, metaphors, strikes by workers, disasters and reactions to an attack are not events.
  `pages.yml` gives the app `mapUrl`.

- **Energy page: the physical prices, honest times and readable news** (2026-10-17, the owner: 'bliver ikke opdateret
  ofte … priserne passer ikke'). The physical prices come from EIA's own pages (FRED never answered GitHub, so 'Det
  fysiske marked' had no physical row and every pass waited 30 s); a failed source rests 30 minutes; a chain's change
  time is its list price's, not one station's; on a weekend the page says the exchanges are closed; a futures price a
  trading day behind the others is shown with its time; the news use the editor's headlines and leave out the wire's
  machine-translated one-liners. The pump list prices were checked against OK's own (17,69 / 18,89 on 17/10): right.

- **Text selection in reading text** (2026-10-17, the owner's yes; `?v=20261017w`): a summary, the lede and the
  movement's texts can be selected and copied; rows, buttons and bars stay unselectable, and the owner's long press
  skips reading text. The owner also said yes to the energy link at the front page's foot and in oil stories, and to
  shared texts ending with 'via khabar.nu/?item=…' – both already in the professional build.

- **Merge: the plain texts of main into the professional build** (2026-10-17; `?v=20261017v`). The professional build
  keeps its structure (the reader's byline and headings, the wiki's contents row, 'Gennem årene' as dated rows under
  their year headings, without the lead's own); main's rule holds everywhere in it: the texts never say 'Ifølge …',
  each Hizb ut-Tahrir block carries one label ('Hizb ut-Tahrirs svar · d/m/åååå' in the reader's byline, on a wiki
  lead, the course, the timeline and the relations), the timeline's rows their small date as the way to the answer, the
  relations a date on each row. The reader's 'Ifølge svaret' / 'Ifølge dette svar og svaret af …' shortening is gone
  (nothing left to shorten). A shared answer or wiki page now carries the label too, since its text no longer says whose.

- **Khabar made professional – the review's fixes** (2026-10-17, the reviewers of the professional build; `?v=20261017pro2`).
  - **Fixed – trust:** the editor's lede is shown whole (it was cut at three lines and hid the Gaza clause; no paragraph
    is a hidden button any more). Dagens historie no longer wears another development: its timeline, and the
    development's name as a clue for the answer line, are used only when the development's name shares a subject with
    the story's headline (a wiki page or a word, never Trump or the USA alone) or the editor filed the story in it – the
    Russia-sanctions story lost 'Iran og angrebet' and the Iran answer (`topicFits` in app.js; the fixed page and an
    opened story's 'Udvikling' too). 'Del dagens overblik' takes one story from each of the editor's blocks in the page's
    order (the main story, then each list's first), only headlines that are checked or a Danish outlet's own plain words,
    no commentary, links without tracking tails (`?referrer=RSS`, `utm_*`). An editor's 'Kreml: …', 'Det Hvide Hus: …'
    stays (the app and `editor.py publish` strip or refuse only news outlets' names, never a government's channel), and a
    headline that names its own row's outlet ('AP: …' on AP) drops it – the outlet is said once, in the meta line. Saving
    a story sends nothing any more (it was counted as a share).
  - **Fixed – red means live or big:** the old-news and offline box is a grey panel with its icon, search marks are bold
    on grey, the settings' switches are the owner's neutral, the focus ring is the text colour, the logo's dot is grey
    while the news are old or the phone is offline, a failing source a hollow dot; a test fails on red anywhere else. The
    chosen chip in dark mode is a chosen segment, not a white pill.
  - **Changed – Gem has a home:** a bookmark in the top bar (filled once something is saved) opens Gemt from every page;
    the save toast says 'Gemt på telefonen · Se Gemt ›'; answers and pages can be taken out of Gemt as stories can; the
    empty page is one line and 'Til Live'; the scattered ways in (the search page's row, Analyser's chip) are gone.
  - **Changed – states and words:** the same cause gives the same message: with no network every page says 'Ingen
    forbindelse …' with its icon; files that failed are fetched again when the network returns; the boxes say the day of
    an old copy ('fra i går kl. 21.34'); the bar shows the offline mark and the copy's time (short at every text size).
    A notification choice made offline is sent when the phone is back online (or at the next start), and a phone that
    signed up before the three switches sends its choice once, so 'Nye svar' is real.
  - **Changed – views:** search puts the news first (developments, then the stories in Live – five under Alle with 'Alle
    n nyheder' –, then the answers, those named in their title first, 'via' last), marks words only where they start
    ('iran' no longer in 'Mirán'), shows ten other headlines with 'Vis flere', and redraws when the answers or the wiki
    arrive. The A–Å index files every page in one of six groups (Stater · Aktører · Steder · Sager · Begreber · Aftaler),
    as one sideways chip row. The coverage count follows one rule everywhere (three outlets and more), and a list of mostly
    one section names the section only on the other stories. Analyser's area filter lasts for the visit. 'Del overblik'
    has its word; the wiki's contents row is chips; its 'I nyhederne nu' and the answer's news have day rows; the
    answer's byline breaks between items; the timeline's ↗ stays with its last word; the Live block's dot follows its
    title; one separator rule in the Live block and the search groups; the search field's ✕ only with text; the day band
    has no second hairline; the catch-up line's counts are 44 high and never leave a '·' at a line's end; the timeline
    under Dagens historie takes its own development's colour; the iPhone hint counts as shown only when Forside showed it.
  - **Radar:** a story is 'Kommentar' only when every readable article of it is commentary, and a news report leads
    before a column (`lead_comment`, 0.6); commentary is never notified; a notification says 'Topnyhed' only for the
    app's five of the day (`top_now`, the same rule as the app), else 'Vigtig nyhed'; a new answer's notification is in
    Danish (machine-translated title, else 'Et nyt svar på politiske spørgsmål').
  - **Speed:** the offline library is fetched once per build of the wiki, not every visit, and not parsed until a page
    needs it. Measured before and after (docs/hjerne/notes-r2-speed.md, 'Review fixes').

- **Khabar made professional** (the owner's request of 2026-10-17: "Gennemgå alle sidens funktioner og
  brugervenlighed …"; docs/hjerne/pro-plan.md, built in full). The look stays khabar.nu; it is refined.
  - **Changed – the visual system:** eight type sizes instead of 28 (`--fs-*` tokens), and the text size now reaches
    the top bar, the tabs and the settings too (capped at 1.2 there); two voices – the app's sans for Khabar and the
    outlets (the lede, development names, quotes), the serif only for Hizb ut-Tahrir's text; one spacing scale, one set
    of corner radii, 1 px lines; red only for live and big – the block titles lost their red dot, the date and the day
    pill are quiet, 'Topnyhed' goes to at most the five strongest big stories of the day for twelve hours; the chosen
    segment in dark mode stands out instead of looking pressed in; every text colour reaches 4.5:1 in all eight palettes
    (Papir's and Apple's third text colour a shade stronger); one icon set (back, bookmark, refresh, offline added; the
    › and ↗ glyphs became icons); headlines and outlet names are never cut – a headline gets four lines and the row
    grows, the meta line breaks between its items; buttons, chips, minis and segments reach 44 pt.
  - **Changed – the views:** Forside – a three-line lede (a tap opens Udvikling), the answer line right under the main
    story, its development named and opened by its label, lists of one section without the section word, a Live block
    with its own header and the page's only red dot, an oil and fuel price row at the foot, the fixed page's 'Danmark'
    block. Live and an opened story – commentary labelled 'Kommentar', teasers without calls to action, links or picture
    captions, one credit line, up to three wiki chips, 'Udvikling: <name> ›', an oil row where the text names oil.
    Udvikling – its own address (?forlob=), share and copy per card, a long history three days at a time, its name in
    view while one reads it. Analyser – one title line, a strip under the bar with the search field and one row of chips
    (Begreber A–Å, Gemt, the areas as a filter, the years), why a hit matched ('via Khilafah'), rows as links, opened
    answers quieter. The answer reader – share, a pointer to a newer answer on the subject, the later answers that cite
    it, today's news on it. A wiki page – a contents row, its paired page, share, today's news under the lead, dated rows
    in 'Gennem årene'. A–Å – a kind filter, the most used pages, a state's issue under it, letters that stay in view.
    Tabs – Analyser stays selected on its own sub-pages. Settings – Energi and the install guides under 'Mere'. The
    intro's three lines match the app; links into the app skip the intro.
  - **Added – five functions:** **Gem** (stories, answers and wiki pages saved on the phone, readable offline; the
    library fetched quietly after the first visit to Analyser); **one search** over news, developments, wiki pages and
    answers with scopes and the last five searches; **Mens du var væk** (one line of what came after three hours away);
    **Del dagens overblik** (the day's top stories as a WhatsApp text); **notifications by choice** (top stories, the
    recap at 21, new answers from Hizb ut-Tahrir – a new kind).
  - **Fixed – states and trust:** a first start without network no longer shimmers for good (a message and 'Prøv igen'
    after four seconds, a reload when the network returns; the bar says 'offline · 10.53' over the phone's copy); a
    missing answer text or wiki page offers 'Prøv igen'; unknown pages and a story that left Live say so with a way on;
    a share sends the summary on screen, not the outlet's teaser, and a link back into Khabar (?item=, ?svar=, ?begreb=,
    ?forlob=); an answer shows once on the front page; one time format ('kl. 10.16', 'i går kl. 21.34', '12/10') and
    timelines newest first with day rows; one word set ('udvikling' and 'opdatering'). Accessibility: tab panels, the
    pages not in view hidden from screen readers, a row read once, headings for days, years and letters, new stories
    read aloud.
  - **Radar and editor:** teasers cleaned at intake (`headlines.clean_teaser`); `kind: 'kommentar'` from the outlets'
    opinion sections and labels, carried in app.json and the editor's input, never a main story; the notification uses
    the editor's headline (summaries.json from the digest branch); search.json carries the Danish headline; push kinds
    per phone (`want`) and a notification for a new answer; `editor.py publish` refuses a lede that repeats the main
    story's headline and an outlet named as speaker of a story it does not carry, and the check notes a timeline that
    is another development; the movement build drops working labels ('ÆNDRING:'), with a test.
  - Tests: tests/test_app_pro.py, test_app_contrast.py, test_pro.py; the speed tests follow the new type scale and
    rows. Speed measured before and after (docs/hjerne/notes-r2-speed.md, 'Professional build').

- **'Ifølge Hizb ut-Tahrir' is gone from the texts** (the owner, 2026-10-17: "Kan vi godt fjerne 'ifølge Hizb
  ut-Tahrir' – det står over det hele"). The 2,615 readings, notes, leads and histories of the movement layer and the
  wiki are written in plain Danish without their attribution ('Ifølge svaret er Saudi-Arabien underordnet USA' →
  'Saudi-Arabien er underordnet USA'); the meaning, hedges and dates are kept, a span of answers stays in brackets
  ('(svarene 2013–2015)', '(svaret af 1/7/2004)' where a lead gathers several answers). `docs/hjerne/uden-ifolge.json`
  holds every plain form; `build_movement.py` and `build_begreber.py` apply it as their last step, and their checks now
  say that no shown text names the movement and that every text sits under a dated answer. The app says whose and when
  once per block: 'Hizb ut-Tahrirs svar · d/m/åååå' on a wiki lead (the lead's answer opens from its title), on the
  timeline and the relations a date on every row (the year bands are gone), and the reader's header in the same form;
  the reader's 'Ifølge svaret' shortening is removed. The editor writes a new answer's note and readings plain
  (`voice.check_plain`, the routine prompt's 'answer' bullet; the live routine's prompt needs the same change –
  docs/hjerne/launch-done.md). App v20261017u.

- **The brain weighs the news; the app shows no analysis** (the owner's decision of 2026-10-17, replacing the Khabar 2
  app): the books' order of importance and Hizb ut-Tahrir's newest answers are used only to select and order the news –
  by the radar's ranking and the editor's front page. One Live section, a front page the editor makes, an Analyser tab
  with the amir's answers, and a wiki of the concepts named in the news compiled only from those answers. The look stays.
  - **Radar** (`src/radar/method.py`, `config/method.json`): every story gets one of the books' 13 tiers, the powers as
    the newest answers read them (USA leading; Britain and France weakened great powers; Russia a middle power since
    12/6/2026; China a regional power; Germany and the EU actors). Lifts 1:+10 … 13:−8, positive ones only when an
    established outlet carries the story; stories of tiers 1–4 and 6 with rank ≥ 45 reach the editor below the taste bar
    (at most 20 a day, `method: true`). Danish politics keeps its place (9 of the top 40, 7 of the top 20). Every source
    has its camp; 31 added sources (TASS, Xinhua, IRNA, Asharq Al-Awsat, the White House, UN News, Le Monde …) with
    `"scale": false` never move the established sources' scale and lead at most `max_added_per_day` = 3 cards a day;
    the movement's own outlets never count as an outlet or confirmation. New story fields: members, camps, first,
    actors, tier, tags, powers, method. `src/radar/analyses.py` (on in radar.yml) keeps the text of the amir's answers
    the static layer does not hold yet. `scripts/rank_check.py` shows Live as one list with tiers (`RANK_CHECK_OUT`,
    `RANK_CHECK_STATE`). Notes: docs/hjerne/notes-radar.md.
  - **Sources** (`config/feeds.json`): every source judged by how well it serves the editor, measured on 4.9 days of
    real data (informative vs curiosity headlines, weight by the books' order, first and unique, the editor's picks,
    health): six removed (Islamisk Viden, DIP Podcast, Kristeligt Dagblad, Weekendavisen, Islam21c, TV Midtvest), 36
    verified new ones (AFP's wire, Reuters and AP, state agencies of the Muslim world, governments' and four Danish
    ministries' own channels, Naharnet, Rudaw, Kyiv Independent, Libya Herald, Dabanga, Yonhap); each source carries a
    measured `fit` (0.5–1.3) for the radar's rank and lead outlet to use (not read by the radar yet). Notes:
    docs/hjerne/kilder-maaling.md, kilder-nye.md.
  - **Editor** (`scripts/editor.py`): looks every quarter of an hour – four routines at minutes 0, 15, 30, 45 – and
    `check` (at most ~40 lines) says INTET NYT AF VÆGT or OPDATÉR: why (a big story, a tier 1–3 story with two outlets, a
    new answer, two hours without an update, the first run after 06 and after 21). Small updates keep the lede, picks
    and quotes; `input` carries the brain (`scripts/brain.py`, ≤ 6,000 characters: the order of weight and each power's
    current reading, dated and attributed) and the front page now; the editor's text is checked by `scripts/voice.py`
    (reality only, the content rules); a new answer is filed in `answers.json` on the digest branch; `--push` refuses
    when another update landed meanwhile. About three to six times today's tokens (docs/hjerne/cadence.md). Notes:
    docs/hjerne/notes-editor.md.
  - **Wiki** (`public/viden/begreber.json`, `begreber-index.json`; `scripts/build_begreber.py` over the movement layer
    `scripts/build_movement.py` and the concept pages `docs/hjerne/begreber-ideer.json`): 203 pages – 67 states, 7
    powers, 4 groups, 34 issues, 90 concepts, agreements, places, organisations and processes – with 526 Danish news
    aliases; every lead, timeline row and relation attributed and dated, the newest answer governing. Notes:
    docs/hjerne/notes-begreber.md, notes-begreber-ideer.md.
  - **App**: three tabs, **Forside · Live · Analyser** (Danmark, Mellemøsten and Verden are gone; Live holds every story
    with its section dot; old `?tab=dk|me|world` links and notifications open Live). The front page is as before, plus
    one quiet line under Dagens historie – and in an opened story – when the amir has answered on its subject
    ('Hizb ut-Tahrirs svar · d/m/åååå' over the title, to the answer reader). Concepts named in the lede, an opened
    story, the recap lines and the timeline link their wiki page (the first mention, at most three a block, a dotted
    underline; never inside a button – a row's tap now lies under its words). A wiki page: the lead, 'Gennem årene',
    relations, the answers, related pages and today's stories that name it. Analyser: the newest answers first, the 321
    by year, a search field and the wiki's A–Å index; the answer reader shows the question, 'Svaret kort', what it reads,
    its concepts, the answers it cites, the text when held and the original. Everything that is the movement's is set
    in a serif on a soft ochre tint with its attribution. The logo goes back the way one came. The sources list and
    coverage name the new groups. Notes: docs/hjerne/notes-app.md.
- **Review fixes for the brain** (2026-10-17, the reviewers' findings on the hjerne branch):
  - **The quarter-hour look no longer needs 96 Claude runs a day** (routines have a daily run cap): `editor.py gate`
    runs after every radar pass in Actions (no tokens) and fires the editor's routine through its API trigger when the
    look's verdict holds – once per reason (a story by its first article), never while an update is under way, at most
    `editor_fires_per_day` = 12 a day spread over the day with the morning's and the evening's kept, at night only for a
    big story. Replayed on 16 October: 12 updates when the news called for them, about the tokens of today's twelve
    (docs/hjerne/cadence.md). Without the secrets `ROUTINE_FIRE_URL`/`ROUTINE_FIRE_TOKEN` it is a dry run.
  - **The look sees better:** a story is new only when its first article is (a card that changed its lead counted
    again and again); picks and recap stories are marked and call for nothing; a big story of no weight (tier 11, 13)
    waits, a Danish one does not; two hours alone are no reason; the radar's last pass is on the first line and a
    stopped radar is a reason of its own.
  - **The newest answer governs, also after launch:** a reading the editor files in answers.json leads the brain's line
    for its subject and the wiki page's lead in the app; `check` says when filed answers wait for a wiki build. The
    wiki's leads are newest first (27 issue leads rewritten from their own histories, the concept leads reordered,
    a state's newer reading before its older standing, the Gulf states' pages carrying the answer of 5/8/2026); the
    build fails when a lead's first sentence lacks its day or a newer reading exists; the whole history of an issue
    stays on its page as 'Forløbet'.
  - **The wiki's own words are gone:** 'Ingen nyere svar', 'Kuwait nævnes ikke særskilt', '(svarets påstand … er ikke
    gengivet)' and the like are left out; 'Storbritanniens folk' reads 'Storbritanniens tilhængere' (a people is never
    judged); 'vasaller' reads 'underordnede stater'; off-topic rows moved off three pages.
  - **The editor's own text is all checked:** recap lines, topic names and picks' why are reality only; a line or quote
    from the movement's or a government's channel gets the movement's checks; 'Starlink-satellitter' is no reading
    word any more; the prompt names 'martyr' as the one source word written 'dræbt'.
  - **The radar** no longer gives a lone US act tier 2 for a bare 'war' or 'sanctions' (a foreign party must be named),
    nor tier 1 to a headline about the past ('allerede', 'dengang'); Live's top 40 is unchanged, Danish stories 7 of
    the top 20 and 10 of the top 40 as before.
  - **App:** the amir's answer line only where the answer is about the story (a filed answer by its readings, not its
    twenty concepts; a second subject from the headline; reports of the dead and domestic stories need a specific one)
    – 14 of the top 90 stories today, none loose; a new answer's area from its own subjects ('27/9/2026 · Yemen');
    a name's touch area about 44 px high; failed loads say so with 'Prøv igen' instead of 'findes ikke'; the phone's
    back gesture steps back through the side pages and the address follows the page; the answer reader shows only the
    answer's own readings, once, and six central concepts first; issue pages read 'Iran – sagen' and their chips
    '· sag'; Analyser's years and the index's letters as a sliding row of chips; long lists unfold twenty at a time;
    the broadest pages (USA, Storbritannien) link after the specific names; nothing moves under the reader when the
    answer line or the links arrive; 'Vis færre' works again (its helper was missing); moves.json is fetched once.
- **Round 2 of the brain: the editor writes every headline, sets how much Live holds and composes the front page; the
  app is faster** (the owner's rules of 2026-10-17: docs/hjerne/notes-owner-headlines.md, notes-owner-volume.md,
  notes-owner-front.md, notes-owner-sources.md, notes-owner-performance.md):
  - **Informative headlines for every story.** The editor writes its own headline for every story Live shows, Danish
    outlets too – who did or said what, where, never a teaser. The input lists up to 30 stories still without one (big
    first, then the ones the app shows worst); `voice.check_headline` refuses questions, 'Derfor/Se/Her er/Sådan …',
    cliff-hangers, '– video', labels and judgements of its own ('egentlige', 'i virkeligheden') unless they are
    someone's statement. A headline is filed with the story's members, so it survives a change of lead. The app shows
    the editor's headline first; until there is one, the outlet's – or, for a plain curiosity headline, the teaser's
    first sentence or another outlet's plain headline. The opened story names the original ('Originaloverskrift').
  - **The day's level.** The editor sets `få`, `normal` or `mange` and may take a story in or drop one (live.json on
    the digest branch); the radar (`src/radar/level.py`) turns the level into a rank floor and a soft count for the last
    24 hours – få about 30–40 stories, normal 43–56, mange 75–86 on 15–17 October – never cuts a big story or Danish
    politics on Islam, Muslims, integration and foreign policy, keeps what it showed while its rank stays near the line,
    and writes a slim **app.json** (the admitted stories of 48 hours and the big ones: 168 KB against data.json's 979
    KB). Notifications only for stories Live shows. A level holds for the Danish day while the editor publishes at least
    every six hours, through the night until the morning's update; take and drop hold two days, the newest decision on
    a story winning.
  - **The front page composed by the editor** (front.json): blocks in its order – top (Dagens historie with its
    timeline), liste (a titled group, compact or with pictures), udvikling, citat, svar (the amir's answer, attributed),
    live and linje (one line of reality) – checked by `publish` (at most 8 blocks, a story once, its stories in Live,
    titles that never look like day markers). The app draws it with its own pieces; missing, unreadable or older than
    six hours between 06 and 24 (twelve at night), the fixed front page shows.
  - **The sources' fit** leads a story: the most informative outlet's article leads (fit, a Danish headline, a teaser;
    a curiosity headline loses) and fit moves the rank by −5 … +3 – curiosity headlines leading a story of several
    outlets fell from 8 to 1. Filters at intake (feeds.json `drop`/`cut`): Times of Israel's blogs, Jerusalem Post's
    opinion pieces, BT's betting ads, Ahram's sport, Shafaq's prefix, Google News site tails, Telegram's speaker-only
    first lines; the language per post (Daily Islamist's Turkish posts).
  - **Faster and smoother** (measured at 5× slowed CPU): a reload patches the page instead of rebuilding it and keeps the
    row being read in place – no long task while reading or scrolling Live (136–159 ms before), pull to refresh's worst
    frame 170 → 37 ms, back from a side page 163 → 4 ms, scrolling Live's worst frame 85 → 15 ms, the intro's longest
    task 536 → 238 ms; files that have not changed are neither read nor drawn; the four files are fetched side by side;
    no blur on the tab bar, no staggered rise of every row, no colour transitions; rows out of sight are skipped.
  - **Review fixes** (docs/hjerne/notes-r2-review.md): the level no longer lapses between the editor's updates (it held
    only two hours); a dropped big story leaves app.json; without app.json the app shows only what the radar admitted;
    a take today undoes yesterday's drop; round 1's curiosity headlines are written anew and removed; the channels'
    names for Israel ('den zionistiske fjende', 'besættelsesstyrker' in Israel's place) and 'heroisk' are refused in the
    editor's own voice; a story whose lead changes keeps its place, stays open and does not glow as new; the front
    page's Live strip no longer repeats the main story; at large text the headlines get a third line and the main
    story's its full three; a failed picture is not fetched again at every reload; redraws wait for the finger; every
    story that waited 45 minutes for its headline counts; a composition's day lines do not cross midnight.
  - Notes: docs/hjerne/notes-r2-editor.md, notes-r2-radar.md, notes-r2-app.md, notes-r2-speed.md, notes-r2-review.md;
    the deploy checklist: docs/hjerne/launch.md.
- New page khabar.nu/energi (link in Indstillinger): 'Lige nu' in wire style (Brent, physical oil against paper, the forward curve, the diesel margin, the cheapest pump price), then Råolie (Brent and WTI futures and physical spot), Det fysiske marked (physical minus paper Brent, the forward curve with backwardation/contango, Brent−WTI), Raffinørmargin (3-2-1, diesel and gasoline cracks), Benzin, diesel og jet (futures and New York/Gulf spot), Danmark (every chain's list price at Circle K, INGO, Q8 and F24 with premium and HVO, the cheaper single stations, the raw product's share of a litre, prices in kroner and the dollar), Gas (TTF, Henry Hub) and the energy stories of the last three days. Every price opens in place into a chart you can touch (1, 3 or 6 months) with what it is and where it comes from. The radar job fetches the numbers after each pass (`src/radar/energy.py` → `energy.json` on the data branch); pump prices are kept one point a day from 17 October 2026.
- More core words for the great-power contest, from the owner's reading of geopolitics: NATO, the Security Council and veto, the straits (Hormuz, Bab el-Mandeb, Suez, Bosporus), military bases, coups, nuclear weapons, blockades, peace plans and normalisation, great powers, the Pentagon, the Kremlin, the White House, BRICS and the IMF (also in Arabic). On today's data a few such stories rose into the top 40 of Mellemøsten and Verden.
- Light news (weather, royals, sport, celebrities) loses 30 rank points instead of 20, as the owner asked (`rank_trivia` in config/settings.json). On today's data the top of every section is unchanged; one light Danish story fell below the list. `scripts/rank_check.py` works again (its stand-in for notifications took too few arguments).
- Live can be sorted: 'Seneste' (everything as it comes in, as before) or 'Vigtigste' (the last 24 hours by weight – the editor's picks first, then the radar's strongest – with pictures, 30 at a time). The phone remembers the choice; a story opened in Live from elsewhere shows in Seneste.
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
