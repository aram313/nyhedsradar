# Kildemåling: hvilke kilder passer bedst til redaktøren

*Målt natten til 17. oktober 2026 på radarens egne data. Alle tal for hver kilde står i `kilder-maaling.json` ved siden af
denne fil. Intet i `config/feeds.json` er ændret – dette er målingen og forslagene.*

Ejerens ønske: *"Gennemgå også kilderne, og se om der er nogle, der passer bedre til redaktøren end andre."* Alle 93 kilder
er målt på det, de faktisk har leveret de seneste dage – ikke på deres ry: hvor tit overskriften siger nyheden, hvor tit
historien vejer efter bøgernes rækkefølge, hvor meget let stof der er, hvor tit kilden er først eller alene om en historie,
og hvor tit redaktøren har valgt dens historier.

## Kort fortalt

- **Ni kilder passer bedst til redaktøren og bør styrkes:** Al-Monitor, Middle East Eye, Al Jazeeras breaking-kanal,
  Altinget, Anadolu, DR's politiske redaktion, Middle East Monitor, QudsN og DR. Deres overskrifter siger nyheden (84–100 %
  informative), de udenlandske har mange vægtige historier (vægt 44–54 %), Altinget og DR Politik er næsten kun dansk
  politik, og redaktøren har valgt dem oftest (23–32 % af historierne fra Al-Monitor, Altinget, Middle East Eye, Middle East
  Monitor og QudsN). DR har de mest informative danske overskrifter af alle (0 % nysgerrighed) og bør lede danske historier.
- **Al Jazeeras breaking-kanal bærer resuméet:** 211 af de 390 linjer, redaktøren skrev 10.–16. oktober, kom derfra.
- **De svageste for redaktøren er de syv regionale TV 2-feeds.** De står for 204 af de 626 danske emner om dagen – en
  tredjedel – men vejer kun 10–13 %, har 17–30 % let stof (trafik, vejr, lokal kriminalitet), og på 4,9 døgn havde de én
  eneste overskrift om islam eller muslimer. Dæmp seks af dem; fjern TV Midtvest, som ikke var alene om én eneste historie,
  der nåede appen.
- **Flest nysgerrighedsoverskrifter** (spørgsmål, "Derfor …", "Se …", "Her er …", kolon-cliffhangere, citater uden
  afsender, opslag der kun er "X on Y:"): BBC Arabic 38 %, DW 32 %, CNN Arabic 25 %, Politiken 24 %, Al Jazeera arabisk og
  Daily Islamist 23 %, Clash Report 22 %, Ekstra Bladet 21 %. De dæmpes, så en anden kildes informative overskrift leder
  historien, når flere har den. **Færrest** blandt kilderne i drift: DR og Al Jazeera breaking 0 %, Anadolu, Reuters og
  QudsN 2 %, AP 3 %, Middle East Eye og Dawn 4 %.
- **Seks kilder bør fjernes** – død, forældet eller ren støj: Islamisk Viden (intet nyt siden februar 2014), DIP Podcast
  (nyeste video 23. september, og YouTube afviser ofte radarens kørsel på GitHub; 0 emner), Kristeligt Dagblad og
  Weekendavisen (Google News har intet nyt fra dem; 0 emner på 4,9 døgn), Islam21c (essays, ca. ét om ugen; 0 emner i de
  målte døgn) og TV Midtvest. Ingen af dem er en lejrs eneste kilde.
- **Lead-overskriften på historier med flere medier er mest i orden:** af 974 sådanne historier havde 59 (6 %) en
  nysgerrigheds-, kommentar- eller tom overskrift som lead, og i 40 af dem havde et andet medie i samme historie en
  informativ dansk eller engelsk overskrift. Med fit-værdierne kan radaren vælge den – omkring 8 historier om dagen. De
  mange historier med kun ét medie får redaktørens egen overskrift efter den nye regel.
- **31 kilder kører ikke endnu.** De blev lagt i feeds.json 11. oktober (Khabar 2) og ligger nu på hjerne-grenen, men ikke på
  main, som radaren kører fra. Radaren har derfor ingen data om dem; de er målt på ét live-udtræk (17. oktober kl. 01.37,
  markeret med \* i tabellerne). Alle 31 svarer og har friske emner. De fleste beholdes. Svage er Ahram Online (37 % sport),
  SVT (mest svensk indland og sport), Pakistans APP, AKIpress og Antara (lokal forvaltning og pressemeddelelser) – de
  dæmpes, og Ahram, AKIpress og Antara bliver, fordi de er deres lejrs eneste kilde.
- **Danske historier om islam og muslimer er sjældne:** 11 overskrifter i alle 25 danske feeds på 4,9 døgn – BT 4,
  Berlingske 3, og Jyllands-Posten, Ekstra Bladet, TV 2 Fyn og DR Regionale 1 hver. Dansk politik i bred forstand kommer
  mest fra BT (10 overskrifter om dagen), Berlingske (7), Politiken og Jyllands-Posten (3 hver) og Altinget (2,6). BT er
  støjende (153 emner om dagen, 22 % let stof, 27 spillereklamer fra Expekt på 4,9 døgn), men bliver: den er ofte først
  (36 %), alene om 50 historier, der nåede appen, og har flest af de få danske historier om muslimer.

## Hvad tallene betyder

- **Informative overskrifter:** andelen, der siger nyheden (hvem gjorde eller sagde hvad). Resten er
  nysgerrighedsoverskrifter (spørgsmål, "Derfor …", "Se …", "Her er …", "Sådan …", tabloid-etiketter som "Klamt fund:",
  citater uden afsender, opslag der kun er "X on Y:"), kommentarer og blogs, eller tomme sider.
- **Vægt:** hvor tungt kildens historier vejer efter bøgernes 13 trin (`config/method.json`): den førende stats handlinger og
  den førende stat med en anden magt 100 %, stormagternes handlinger, magtskifter og kampagnen mod islam 90 %, dansk politik
  80 %, de store sager (Mellemøsten først) og redskaberne 50 %, resten 10 %, let stof 0 %. *Skarpe historier* (i
  JSON-filen) er trin 1–4 og 6 – og for danske kilder dansk politik, islam og indvandring.
- **Let stof:** sport, vejr, kongehus, kendte, trafik og lokal kriminalitet (radarens egne ord og tilsvarende på de andre
  sprog).
- **Redaktøren valgte:** andelen af kildens historier, som redaktøren tog som pick, skrev sin danske overskrift til eller
  resumerede (i parentes antallet).
- **Først:** hvor tit kilden var den første i radaren på en historie, som flere medier havde.
- **Ene om … i appen:** historier, hvor kilden var det eneste medie, og som nåede appen.
- **Fit:** forslaget til radarens vægt for kilden – 1,0 er neutral, over 1 løfter, under 1 dæmper. Den bruges lidt i
  rangeringen og især til at vælge, hvilket medies overskrift og teaser der leder en historie, flere har: den mest
  informative, ikke den mest sensationelle. Forslagene ligger mellem 0,6 og 1,2 (0,5 for de kilder, der bør fjernes).
  Regeringers egne kanaler, bevægelsens egne medier og kanalerne leder aldrig en historie, et etableret medie har –
  uanset fit.

## Forslagene

Udgangspunktet er én formel for alle kilder (informative overskrifter, vægt, let stof, redaktørens brug, først, teaser),
skrumpet mod 1,0, når der er få overskrifter at måle på. Hvor tallene alene ville vildlede, er fit justeret med en
begrundelse (formlens værdi står som `fit_formula` i JSON-filen). Eksempel: Reuters vælges sjældent af redaktøren, fordi
det meste er marked og erhverv, men når Reuters har en historie, er dens overskrift den mest informative – derfor 1,05 og
ikke formlens 0,94.

### Styrk (9)

| Kilde | Lejr | Om dagen | Informative overskrifter | Vægt | Let stof | Redaktøren valgte | Først | Fit | Hvorfor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Al-Monitor | USA | 22 | 91 % | 54 % | 0 % | 32 % (31) | 38 % | 1,20 | redaktøren valgte 32 %, vægt 54 %, først på 38 %; informative overskrifter (91 %, også Reuters/AFP-kopi) |
| Middle East Eye | muslimer i Vesten | 62 | 95 % | 53 % | 0 % | 24 % (66) | 21 % | 1,20 | informative overskrifter (95 %), vægt 53 %, redaktøren valgte 24 % (66 historier); ingen teaser via Google News |
| Al Jazeera breaking (الجزيرة عاجل) | Qatar | 126 | 100 % | 53 % | 0 % | 6 % (33) | 53 % | 1,20 | rygraden i redaktørens resumé: 211 af 390 linjer (54 %) kommer fra denne kanal; 0 % nysgerrighed; først i radaren på 53 % af sine historier |
| Altinget | Danmark | 3,9 | 84 % | 65 % | 0 % | 30 % (10) | 67 % | 1,15 | dansk politik i ren form: 74 % skarpe historier, vægt 65 %, redaktøren valgte 30 %, ene om 16 historier i appen; men mange debatindlæg og ingen teaser |
| Anadolu | Tyrkiet | 129 | 98 % | 44 % | 1 % | 11 % (70) | 31 % | 1,15 | informative overskrifter (98 %) med teaser, leder allerede 117 historier, ene om 43 i appen, redaktøren valgte 70; tyrkisk statsbureau – vinklen er Ankaras |
| DR (DR Politik) | Danmark | 1,8 | 89 % | 57 % | 0 % | 17 % (4) | 0 % | 1,15 | DR's politiske redaktion: 67 % skarpe historier, ene om 15 historier der nåede appen; få egne emner, fordi DR's hovedfeed tager de fleste først |
| Middle East Monitor | muslimer i Vesten | 16 | 92 % | 49 % | 1 % | 23 % (30) | 18 % | 1,15 | informative overskrifter (92 %), redaktøren valgte 23 %, ene om 24 historier i appen |
| QudsN | kanaler | 83 | 98 % | 50 % | 1 % | 23 % (59) | 29 % | 1,15 | informative opslag (98 %), redaktøren valgte 23 % (59 historier), først i radaren på 29 %; en kanal – bekræfter ikke |
| DR | Danmark | 15 | 100 % | 22 % | 23 % | 13 % (12) | 20 % | 1,10 | Danmarks mest informative overskrifter (0 % nysgerrighed) – bedste danske lead; 23 % let stof dæmpes af radarens egne ord |

For Al Jazeeras breaking-kanal betyder *styrk*: behold den som resuméets rygrad; den bliver aldrig et kort i sig selv.

### Dæmp (25)

| Kilde | Lejr | Om dagen | Informative overskrifter | Vægt | Let stof | Redaktøren valgte | Først | Fit | Hvorfor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| TV Syd | Danmark | 38 | 82 % | 10 % | 30 % | 3 % (5) | 56 % | 0,60 | regional støj for redaktørens job: 38/dag, vægt 10 %, 30 % let stof, 0 overskrifter om islam/muslimer på 4,9 døgn; ene om 3 historier i appen |
| TV 2 Fyn | Danmark | 28 | 93 % | 12 % | 20 % | 6 % (7) | 41 % | 0,70 | regional støj for redaktørens job: 28/dag, vægt 12 %, 20 % let stof, 1 overskrift om islam/muslimer på 4,9 døgn; ene om 5 historier i appen |
| TV 2 Kosmopol | Danmark | 23 | 95 % | 13 % | 21 % | 7 % (8) | 29 % | 0,70 | regional støj for redaktørens job: 23/dag, vægt 13 %, 21 % let stof, 0 overskrifter om islam/muslimer på 4,9 døgn; ene om 4 historier i appen |
| TV 2 Nord | Danmark | 27 | 90 % | 10 % | 19 % | 3 % (3) | 38 % | 0,70 | regional støj for redaktørens job: 27/dag, vægt 10 %, 19 % let stof, 0 overskrifter om islam/muslimer på 4,9 døgn; ene om 3 historier i appen |
| TV 2 Øst | Danmark | 23 | 90 % | 13 % | 18 % | 7 % (7) | 28 % | 0,70 | regional støj for redaktørens job: 23/dag, vægt 13 %, 18 % let stof, 0 overskrifter om islam/muslimer på 4,9 døgn; ene om 6 historier i appen |
| TV 2 Østjylland | Danmark | 32 | 94 % | 12 % | 17 % | 5 % (7) | 34 % | 0,70 | regional støj for redaktørens job: 32/dag, vægt 12 %, 17 % let stof, 0 overskrifter om islam/muslimer på 4,9 døgn; ene om 3 historier i appen |
| Ahram Online * | Egypten | 31 | 89 % | 32 % | 37 % | – | – | 0,75 | 37 % sport (" - Sports"); lejrens eneste kilde, så den bliver – dæmpet; sportsoverskrifterne bør filtreres |
| SVT Nyheter * | Sverige/Norge | 36 | 96 % | 12 % | 0 % | – | – | 0,75 | mest svensk indland og en del sport (vægt 12 %); bliver for den svensk-norske lejr (med NRK) |
| BBC Arabic (BBC عربي) | Storbritannien | 12 | 57 % | 47 % | 0 % | 17 % (12) | 0 % | 0,75 | 38 % nysgerrighedsoverskrifter (spørgsmål, "لماذا", "هل"); først 0 %; den britiske lejr har fire andre medier |
| AKIpress * | Centralasien | 34 | 100 % | 30 % | 0 % | – | – | 0,80 | mest kirgisisk forvaltning og lokalstof (vægt 30 %); lejrens eneste kilde, så den bliver – dæmpet |
| Daily Islamist | kanaler | 8,9 | 77 % | 50 % | 0 % | 8 % (5) | 19 % | 0,80 | halvdelen af opslagene er på tyrkisk (står som engelsk i feeds.json), 23 % overskrifter er kun "Navn:" uden indhold; 0 historier i appen alene |
| DW | Tyskland | 7,5 | 68 % | 39 % | 0 % | 14 % (6) | 36 % | 0,80 | 32 % spørgende overskrifter ("Can Kenya …?", "What's behind …?"); lejrens eneste kilde, så den bliver – dæmpet, ikke fjernet |
| DR (DR Regionale) | Danmark | 3,7 | 89 % | 13 % | 11 % | 0 % (0) | 100 % | 0,80 | regionalt stof (vægt 13 %, 11 % let), 3,7 om dagen; DR's andre feeds dækker det vigtige |
| Ekstra Bladet | Danmark | 59 | 79 % | 15 % | 18 % | 7 % (20) | 34 % | 0,80 | 21 % nysgerrighedsoverskrifter (tabloid-etiketter: "Klamt fund:", "Slår alarm:"), 18 % let stof, vægt 15 %; leder 62 historier, 8 med en nysgerrighedsoverskrift |
| Ekstra Bladet (Ekstra Bladet Nyheder) | Danmark | 2,8 | 93 % | 29 % | 14 % | 36 % (5) | 56 % | 0,80 | Ekstra Bladets nyhedsfeed: samme stil som hovedfeedet, kun 2,8 egne emner om dagen |
| Associated Press of Pakistan (APP) * | Pakistan | 45 | 100 % | 14 % | 0 % | – | – | 0,80 | Pakistans statsbureau, men mest lokal forvaltning (vægt 14 %); Dawn dækker lejren bedre |
| Clash Report | kanaler | 130 | 78 % | 42 % | 0 % | 8 % (49) | 46 % | 0,85 | hurtig (først på 46 %) men en genopslagskanal: 22 % overskrifter er kun "X on Y:" uden indhold, og stoffet blander Tesla og krig |
| Information | Danmark | 9,3 | 80 % | 26 % | 2 % | 6 % (4) | 10 % | 0,85 | 20 % nysgerrighedsoverskrifter, mest analyse; redaktøren valgte kun 6 % af dens historier |
| Politiken | Danmark | 39 | 75 % | 22 % | 4 % | 10 % (14) | 18 % | 0,85 | 24 % nysgerrighedsoverskrifter (spørgsmål, "Han …", "Hun …"), vægt 22 %; redaktøren valgte 10 % |
| Politiken (Politiken Indland) | Danmark | 4,3 | 81 % | 35 % | 0 % | 0 % (0) | 100 % | 0,85 | Politikens indlandsfeed: samme overskriftsstil, få egne emner (4/dag) |
| Politiken (Politiken Udland) | Danmark | 2,6 | 77 % | 25 % | 0 % | 0 % (0) | 0 % | 0,85 | Politikens udlandsfeed: samme overskriftsstil, få egne emner (2,6/dag) |
| Antara * | Indonesien | 59 | 100 % | 37 % | 2 % | – | – | 0,85 | Indonesiens statsbureau, men meget lokalt Jakarta-stof og pressemeddelelser; lejrens eneste kilde, så den bliver – dæmpet |
| Al Jazeera (arabisk) (الجزيرة) | Qatar | 139 | 77 % | 47 % | 2 % | 8 % (57) | 17 % | 0,85 | 139/dag, 23 % nysgerrighedsoverskrifter; arabisk alene er altid "unik" (arabiske emner samles aldrig med hinanden); redaktøren valgte 8 % |
| The Guardian | Storbritannien | 66 | 94 % | 20 % | 5 % | 3 % (9) | 32 % | 0,85 | 66/dag, mest britisk og australsk indland (vægt 20 %); redaktøren valgte 3 % (9 af 352 historier) |
| CNN Arabic (CNN بالعربية) | USA | 48 | 73 % | 43 % | 4 % | 11 % (25) | 19 % | 0,85 | 25 % nysgerrighedsoverskrifter ("شاهد..", "إليكم ما حدث"); den amerikanske lejr har AP, NYT og Al-Monitor |

\* målt på et live-udtræk 17. oktober kl. 01.37, fordi kilden ikke kører endnu.

### Fjern (6)

| Kilde | Lejr | Om dagen | Informative overskrifter | Vægt | Let stof | Redaktøren valgte | Først | Fit | Hvorfor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| DIP Podcast * | kanaler | 0,0 | – | – | – | – | – | 0,50 | nyeste video er fra 23. sep. – ældre end kildens grænse på 14 døgn – og YouTube afviser ofte radarens kørsel på GitHub (op til 66 kørsler i træk); 0 emner på 4,9 døgn; podcast-titler er ingen nyheder |
| Islamisk Viden * | kanaler | 0,0 | – | – | – | – | – | 0,50 | død: nyeste video er fra 25. feb. 2014 |
| Kristeligt Dagblad * | Danmark | 0,0 | – | – | – | – | – | 0,50 | Google News har intet nyt fra sitet (nyeste 113 døgn gammelt, også med when:1d/7d); /rss giver en webside |
| TV Midtvest | Danmark | 33 | 85 % | 10 % | 18 % | 3 % (4) | 39 % | 0,50 | regional støj: 33 emner om dagen, men på 4,9 døgn 0 skarpe historier og 0 historier i appen, som ingen anden havde; 18 % let stof |
| Weekendavisen * | Danmark | 0,0 | – | – | – | – | – | 0,50 | Google News har intet nyt fra sitet (nyeste 274 døgn gammelt, også med when:7d); /rss findes ikke |
| Islam21c * | muslimer i Vesten | 0,0 | – | – | – | 0 % (0) | – | 0,50 | forældet: nyeste indlæg 7,5 døgn gammelt, ca. ét essay om ugen; 0 emner nåede radaren på 4,9 døgn |

\* målt på et live-udtræk 17. oktober kl. 01.37, fordi kilden ikke kører endnu.

### Behold (53)

| Kilde | Lejr | Om dagen | Informative | Redaktøren valgte | Fit | Hvorfor |
|---|---|---:|---:|---:|---:|---|
| Berlingske | Danmark | 50 | 81 % | 20 % (44) | 1,00 | ene om 57 historier der nåede appen (flest af alle) og 26 skarpe; men 19 % nysgerrighedsoverskrifter – godt stof, svagere lead |
| DR (DR Udland) | Danmark | 16 | 89 % | 10 % (9) | 1,00 | DR's udlandsredaktion: vægt 41 %, ene om 19 historier i appen; 11 % forklarende "Sådan …"-overskrifter |
| Jyllands-Posten | Danmark | 25 | 78 % | 23 % (25) | 1,00 | redaktøren valgte 23 % (25 historier, 19 som lead), ene om 24 historier i appen; men 20 % nysgerrighedsoverskrifter |
| DR (DR Indland) | Danmark | 22 | 86 % | 8 % (8) | 0,95 | dansk indland med lav vægt (16 %) og 14 % nysgerrighed, men ofte først (33 %) |
| BT | Danmark | 153 | 90 % | 10 % (61) | 0,90 | største danske kilde (153/dag, 22 % let stof, 27 spillereklamer fra Expekt på 4,9 døgn) men ofte først (36 %), ene om 50 historier i appen og flest af de få danske historier om muslimer (4 af 11) |
| TV 2 | Danmark | 15 | 86 % | 5 % (5) | 0,90 | blandet: 14 % nysgerrighed, 12 % let stof, vægt 14 %; redaktøren valgte 5 % |
| DOAM | kanaler | 4,5 | 68 % | 36 % (10) | 1,00 | dokumenterer overgreb mod muslimer; redaktøren valgte 36 %, men 32 % af overskrifterne er citater uden afsender |
| Stand 4 Palestine | kanaler | 0,4 | 100 % | 33 % (2) | 1,00 | næsten stille (under én om dagen); koster intet, men giver heller ikke meget |
| TMW Media | kanaler | 3,5 | 94 % | 26 % (6) | 1,00 | lille (3,5/dag), informative opslag (94 %), redaktøren valgte 26 %; en kanal – bekræfter ikke |
| Warfare Analysis | kanaler | 28 | 89 % | 16 % (19) | 1,00 | vægt 49 %, redaktøren valgte 16 %; 11 % nysgerrighed; en kanal – bekræfter ikke |
| Quds News (arabisk) (شبكة قدس) | kanaler | 196 | 87 % | 7 % (59) | 0,90 | største kilde af alle (196/dag), men 23 af redaktørens historier fandtes kun her (lokale razziaer, Gazas dødstal); kanal-loftet begrænser den |
| Reuters | Storbritannien | 178 | 98 % | 1 % (9) | 1,05 | informative wire-overskrifter (98 %) og først i radaren på 43 %; men 178/dag mest marked og erhverv (vægt 27 %), og redaktøren valgte kun 1 %; ingen teaser |
| BBC | Storbritannien | 25 | 83 % | 8 % (11) | 0,95 | 17 % spørgende overskrifter ("What we know", "Why …"), vægt 31 %; redaktøren valgte 8 %; den britiske lejr har også Reuters og Guardian |
| The Guardian (The Guardian Mellemøsten) | Storbritannien | 5,1 | 68 % | 13 % (4) | 0,95 | Mellemøsten-redaktionen: vægt 50 %, men 20 % kommentarer; lille feed (5/dag) |
| Storbritanniens udenrigsministerium (UK FCDO) * | Storbritannien | 9,2 | 100 % | – | 0,95 | britisk udenrigsministerium (sanktioner, udtalelser); rejsevejledninger fylder, de fleste sorteres fra ved indtaget |
| New York Times | USA | 3,7 | 83 % | 41 % (11) | 1,05 | redaktøren valgte 41 % af dens historier (højest), men 17 % spørgende overskrifter og kun 3,7 om dagen |
| USA's udenrigsministerium (US State Department) * | USA | 2,7 | 100 % | – | 1,05 | den førende stats udenrigsministerium (opkald, sanktioner); kun 2–3 om dagen |
| AP | USA | 107 | 96 % | 2 % (14) | 1,00 | informative wire-overskrifter (96 %), først på 30 %; 107/dag med lav vægt (21 %), redaktøren valgte 2 %; ingen teaser |
| Det Hvide Hus (White House) * | USA | 3,3 | 100 % | – | 1,00 | den førende stats egen kanal; 7 af 30 er præsidentens hilsner, som metoden selv vægter ned |
| The New Arab | Qatar | 32 | 94 % | 13 % (26) | 1,10 | informative overskrifter (94 %), vægt 48 %, først i radaren på 30 %; ingen teaser via Google News |
| Al Jazeera | Qatar | 76 | 84 % | 12 % (43) | 1,00 | vægtigt (46 %) og meget brugt (43 historier), men 16 % spørgende overskrifter i baggrundsstof |
| 5Pillars | muslimer i Vesten | 1,2 | 83 % | 10 % (1) | 1,00 | lille (1,2/dag), men britiske muslimers egne sager – nyttigt i dawah |
| Daily Sabah * | Tyrkiet | 44 | 100 % | – | 1,05 | regeringsnær tyrkisk avis: informative overskrifter (100 %), vægt 50 %, teaser i alle |
| TRT World * | Tyrkiet | 25 | 100 % | – | 1,05 | informativ (100 %), men 75 af 100 emner fra Google News er tomme sider ("- TRT World"), som radaren sorterer fra – reelt ca. 25/dag |
| Ruslands udenrigsministerium (MFA Russia) * | Rusland | 9,7 | 92 % | – | 1,05 | Lavrovs og udenrigsministeriets udtalelser på engelsk; ca. 10/dag |
| TASS * | Rusland | 177 | 100 % | – | 1,05 | informative overskrifter (100 %) med teaser, vægt 51 %, mest eget stof (kun ca. hver 9. findes hos radarens kilder); mindst 175/dag – Moskvas statsbureau, lejrloftet holder den nede |
| Kreml (Kremlin) * | Rusland | 2,4 | 100 % | – | 0,90 | Putins egne møder og samtaler – regeringens egen stemme; 9 af 20 er hilsner og lykønskninger, som metoden selv vægter ned |
| CGTN * | Kina | 15 | 90 % | – | 1,00 | kinesisk statstv; opdateres ca. én gang i døgnet (nyeste 21 t), 10 % spørgsmål |
| Xinhua * | Kina | 29 | 93 % | – | 1,00 | informative wire-overskrifter (93 %), men vægt 29 % og ingen teaser |
| Global Times * | Kina | 38 | 95 % | – | 0,95 | partiavisens tabloid, hvor Beijings skarpere linje står: informative (95 %), men ingen teaser og vægt 39 % |
| Dawn | Pakistan | 52 | 96 % | 7 % (15) | 1,00 | informative overskrifter (96 %), men mest pakistansk indland (vægt 28 %); eneste pakistanske kilde i drift |
| France 24 | Frankrig | 3,5 | 88 % | 33 % (8) | 1,05 | lille Mellemøsten-feed (3,5/dag) som redaktøren bruger (33 %); 12 % spørgsmål; eneste franske kilde i drift |
| Le Monde * | Frankrig | 13 | 86 % | – | 1,00 | engelsk udgave; 14 % spørgende eller forklarende overskrifter, vægt 21 %; Frankrigs anden kilde ved siden af France 24 |
| Jerusalem Post | Israel | 73 | 79 % | 14 % (47) | 0,95 | 18 % kommentarer/analyser (" - opinion", " - analysis"), som bør filtreres fra; ellers informativ, redaktøren valgte 14 % |
| Times of Israel | Israel | 121 | 79 % | 9 % (58) | 0,95 | 121/dag, heraf 13 % blogs ("The Blogs:"), som bør filtreres fra; ellers informativ (79 %), først på 28 % |
| The National | Emiraterne | 48 | 91 % | 8 % (23) | 1,00 | vægtigt (49 %), men livsstil og Netflix ind imellem, ingen teaser; redaktøren valgte 8 % |
| Sky News Arabia (سكاي نيوز عربية) | Emiraterne | 66 | 87 % | 11 % (41) | 1,00 | vægtigt (47 %), redaktøren valgte 11 %; 13 % nysgerrighedsoverskrifter; arabisk, så den leder kun historier uden dansk eller engelsk version |
| Köklü Değişim | bevægelsen | 1,8 | 100 % | 0 % (0) | 1,00 | bevægelsens egen kanal: bliver, tæller aldrig som bekræftelse og leder aldrig en historie, andre medier har; ca. 2 opslag om dagen på tyrkisk |
| Hizb ut-Tahrir (arabisk) (حزب التحرير) | bevægelsen | 0,8 | 50 % | 0 % (0) | 1,00 | bevægelsens egen kanal: bliver, tæller aldrig som bekræftelse og leder aldrig en historie, andre medier har; meget lille (0,8/dag), nyeste 61 t |
| Al Mayadeen English * | Iran | 34 | 95 % | – | 1,10 | "modstandsaksens" stemme (Iran/Hizbollah): informative opslag (95 %), vægt 53 %, teaser i alle |
| IRNA * | Iran | 20 | 100 % | – | 1,10 | Irans statsbureau: udsagn med navn ("Pezeshkian: …"), 0 % nysgerrighed, teaser i alle |
| Asharq Al-Awsat * | Saudi-Arabien | 58 | 98 % | – | 1,10 | saudiejet avis: informative overskrifter (98 %), vægt 50 %, ca. 58/dag; ingen teaser |
| Saudi Press Agency * | Saudi-Arabien | 8,7 | 96 % | – | 1,00 | Riyadhs egen stemme; noget regnvejr og kultur, og Google News giver også gamle emner (radarens aldersgrænse fjerner dem) |
| The Hindu * | Indien | 132 | 97 % | – | 1,00 | informative overskrifter (97 %) med teaser, mest bureaustof om udland; mindst 130/dag (feedet viser kun de nyeste 60) |
| Indiens udenrigsministerium (India MEA) * | Indien | 6,3 | 100 % | – | 0,95 | Indiens udenrigsministerium; nogle PDF-emner uden titel ("3. The"), som radaren selv sorterer fra |
| NRK Urix * | Sverige/Norge | 1,0 | 100 % | – | 1,00 | NRK's udlandsredaktion; kun ca. én om dagen |
| Europa-Kommissionen (European Commission) * | EU | 6,7 | 90 % | – | 1,00 | EU-Kommissionens egne taler og udtalelser; lejrens eneste kilde |
| FN Nyheder (UN News) * | FN | 3,0 | 78 % | – | 0,90 | FN's egne nyheder; flere emner er oversigtssider ("UN News Today"); lejrens eneste kilde |
| Ariana News * | Afghanistan | 12 | 100 % | – | 1,05 | Afghanistans (Det Islamiske Emirats) udsagn; lejrens eneste kilde |
| AllAfrica * | Afrika | 11 | 91 % | – | 1,00 | samler afrikanske medier ("Nigeria: …"); lejrens eneste kilde |
| WAFA * | Palæstina | 6,0 | 100 % | – | 1,10 | Det Palæstinensiske Selvstyres egen stemme; informative overskrifter; lejrens eneste kilde |
| Enab Baladi * | Syrien | 4,3 | 100 % | – | 1,00 | eneste syriske kilde; 3 af 7 emner er tomme sider, som radaren sorterer fra |
| Shafaq News * | Irak | 33 | 100 % | – | 1,10 | eneste irakiske kilde; informative overskrifter ("Shafaq News..US pauses strikes …") |

\* målt på et live-udtræk 17. oktober kl. 01.37, fordi kilden ikke kører endnu.

## Kilder pr. lejr

Metoden sammenligner, hvordan lejrene fortæller den samme begivenhed, så ingen lejr må stå uden kilde. Ingen af
forslagene fjerner en lejrs eneste kilde. Elleve lejre hviler på én kilde (Afghanistan, Afrika, Centralasien, Tyskland,
Egypten, EU, Indonesien, Irak, Palæstina, Syrien, FN), og af dem kører kun Tyskland (DW) i dag. I alt 16 lejre har ingen
kilde i drift, før de 31 nye kilder kører – de ti andre af de elleve og Rusland, Kina, Iran, Saudi-Arabien, Indien og
Sverige/Norge.

| Lejr | Kilder i alt | Kører i dag | Efter forslaget | Kilderne |
|---|---:|---:|---:|---|
| Danmark | 25 | 25 | 22 | Altinget, BT, Berlingske, DR, DR (DR Indland), DR (DR Politik), DR (DR Regionale), DR (DR Udland), Ekstra Bladet, Ekstra Bladet (Ekstra Bladet Nyheder), Information, Jyllands-Posten, Kristeligt Dagblad, Politiken, Politiken (Politiken Indland), Politiken (Politiken Udland), TV 2, TV 2 Fyn, TV 2 Kosmopol, TV 2 Nord, TV 2 Øst, TV 2 Østjylland, TV Midtvest, TV Syd, Weekendavisen |
| kanaler | 10 | 10 | 8 | Clash Report, DIP Podcast, DOAM, Daily Islamist, Islamisk Viden, Quds News (arabisk) (شبكة قدس), QudsN, Stand 4 Palestine, TMW Media, Warfare Analysis |
| Storbritannien | 6 | 5 | 6 | BBC, BBC Arabic (BBC عربي), Reuters, Storbritanniens udenrigsministerium (UK FCDO), The Guardian, The Guardian (The Guardian Mellemøsten) |
| USA | 6 | 4 | 6 | AP, Al-Monitor, CNN Arabic (CNN بالعربية), Det Hvide Hus (White House), New York Times, USA's udenrigsministerium (US State Department) |
| muslimer i Vesten | 4 | 4 | 3 | 5Pillars, Islam21c, Middle East Eye, Middle East Monitor |
| Qatar | 4 | 4 | 4 | Al Jazeera, Al Jazeera (arabisk) (الجزيرة), Al Jazeera breaking (الجزيرة عاجل), The New Arab |
| Kina | 3 | 0 | 3 | CGTN, Global Times, Xinhua |
| Rusland | 3 | 0 | 3 | Kreml (Kremlin), Ruslands udenrigsministerium (MFA Russia), TASS |
| Tyrkiet | 3 | 1 | 3 | Anadolu, Daily Sabah, TRT World |
| Emiraterne | 2 | 2 | 2 | Sky News Arabia (سكاي نيوز عربية), The National |
| bevægelsen | 2 | 2 | 2 | Hizb ut-Tahrir (arabisk) (حزب التحرير), Köklü Değişim |
| Frankrig | 2 | 1 | 2 | France 24, Le Monde |
| Israel | 2 | 2 | 2 | Jerusalem Post, Times of Israel |
| Indien | 2 | 0 | 2 | Indiens udenrigsministerium (India MEA), The Hindu |
| Iran | 2 | 0 | 2 | Al Mayadeen English, IRNA |
| Pakistan | 2 | 1 | 2 | Associated Press of Pakistan (APP), Dawn |
| Saudi-Arabien | 2 | 0 | 2 | Asharq Al-Awsat, Saudi Press Agency |
| Sverige/Norge | 2 | 0 | 2 | NRK Urix, SVT Nyheter |
| Afghanistan (eneste kilde) | 1 | 0 | 1 | Ariana News |
| Afrika (eneste kilde) | 1 | 0 | 1 | AllAfrica |
| Centralasien (eneste kilde) | 1 | 0 | 1 | AKIpress |
| Tyskland (eneste kilde) | 1 | 1 | 1 | DW |
| Egypten (eneste kilde) | 1 | 0 | 1 | Ahram Online |
| EU (eneste kilde) | 1 | 0 | 1 | Europa-Kommissionen (European Commission) |
| Indonesien (eneste kilde) | 1 | 0 | 1 | Antara |
| Irak (eneste kilde) | 1 | 0 | 1 | Shafaq News |
| Palæstina (eneste kilde) | 1 | 0 | 1 | WAFA |
| Syrien (eneste kilde) | 1 | 0 | 1 | Enab Baladi |
| FN (eneste kilde) | 1 | 0 | 1 | FN Nyheder (UN News) |

## Små rettelser, der gør gode kilder bedre

- **Times of Israel:** 13 % af dens 121 emner om dagen er blogs ("The Blogs: …") – de bør sorteres fra ved indtaget.
- **Jerusalem Post:** 18 % er kommentarer og analyser (" - opinion", " - analysis", " - comment" sidst i overskriften).
- **BT:** spillereklamer ("Premier League Bet Builder hos Expekt: Odds …") – 27 på 4,9 døgn – er ingen nyheder.
- **Ahram Online:** overskrifter, der ender på " - Sports", er sport (37 % af feedet); de øvrige har sektionen hængende
  bagpå (" - Foreign Affairs - Egypt"), som bør skæres af.
- **Shafaq News:** "Shafaq News.." foran hver overskrift bør skæres af.
- **Clash Report, Daily Islamist, DOAM:** 22–32 % af opslagene har en første linje, der kun er "Navn:" eller "X on Y:";
  overskriften bør tages fra næste sætning. Daily Islamist skriver halvdelen af sine opslag på tyrkisk (står som engelsk i
  feeds.json; radaren genkender sproget pr. opslag).
- **Ingen teaser:** kilder via Google News (Reuters, AP, Middle East Eye, Times of Israel, The New Arab m.fl.) samt DR,
  Altinget og The National har ingen indledning. Når en historie har et andet medie med teaser, bør teaseren hentes
  derfra.
- **Huller, målingen viser:** med Kristeligt Dagblad væk har radaren intet dansk medie, der følger religion; Danmarks
  nyhedsbureau (Ritzau) er ikke med; og statsbureauer har radaren kun for Tyrkiet (Anadolu, i drift) og – blandt de 31
  nye – Saudi-Arabien, Palæstina, Pakistan, Iran og Indonesien. De mangler for Qatar, Emiraterne, Egypten, Jordan, Irak
  og Syrien. Nye kilder skal testes, før de lægges ind.

## Sådan er der målt

- **Radarens data:** to øjebliksbilleder af data-grenen – 9.–11. oktober (fra kl. 23.00 til 21.11) og 14.–17. oktober (fra
  kl. 01.30 til 01.29), i alt 4,9 døgn og 12.330 overskrifter fra de 62 kilder, der kører. Historierne er skåret med
  radarens egen kode på radarens egne gemte tekstvektorer; resultatet gengiver radarens egne kort præcist (1.179 af
  1.179 par). Det gav 9.681 historier, heraf 974 med flere medier.
- **Bøgernes vægt:** metoden (`src/radar/method.py` og `config/method.json`, som de stod kl. 01.30) på hver overskrift.
- **Redaktørens valg:** de 13 udgaver af digest-grenen, der findes lokalt (10., 11. og 17. oktober): 418 historier kunne
  kobles til radarens data (27 picks, 257 historier med redaktørens danske overskrift, 229 resuméer), plus 390
  resumélinjer fra 10.–16. oktober. Redaktøren ser kun radarens bedste historier, så hans valg afspejler også radarens egen
  rangering.
- **Først** er målt på, hvornår emnet nåede radaren (den kører hvert 5. minut; Google News-kilder kommer senere end
  Telegram). Målt på mediernes egne tidsstempler er Reuters først endnu oftere (60 %).
- **Arabiske historier** samles aldrig med andre arabiske (radarens regel, fordi modellen finder alle arabiske
  overskrifter ens), så arabiske kilder ser ud til at være alene om mange historier. Det tæller ikke til deres fordel her.
- **De 31 nye kilder** er målt på ét live-udtræk med radarens egen henter (17. oktober kl. 01.37; 3.121 overskrifter fra
  alle 93 kilder). Mængden pr. dag er beregnet ud fra tidsstemplerne i feedet; for feeds, der kun viser et fast antal (TASS
  100, The Hindu 60), er tallet et minimum. Hvor meget de overlapper radarens øvrige kilder, er et skøn ud fra fælles ord i
  overskrifterne. *Først*, *ene om* og *redaktøren valgte* kan først måles, når de kører.
- Kristeligt Dagblad og Weekendavisen er prøvet igen med andre Google News-søgninger (`when:1d`, `when:7d`) og med deres
  RSS-adresser: ingen nye emner.
