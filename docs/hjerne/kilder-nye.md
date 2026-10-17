# Nye kilder til redaktøren (17. oktober 2026)

Ejerens ønske: "find også gerne nye, bedre kilder". Jeg har prøvet godt 150 mulige kilder. De 36 herunder virker alle.
Jeg hentede dem i nat (17/10) på samme måde, som radaren læser dem. Hver kilde svarede, havde nye historier, læsbare
overskrifter og links, der åbner. Tallet i parentes er mit gæt på kildens *fit*: hvor godt den tjener redaktøren.

Regeringer og statsbureauer står som officielle kilder. De fører aldrig en historie, som et almindeligt medie også bringer.
Og de giver højst nogle få kort om dagen, så deres ceremonier ikke fylder i appen. Alle data og webadresser står i
`kilder-nye.json` i samme form som `config/feeds.json`. Mine egne felter (verified_at, why osv.) skal fjernes,
når en kilde lægges ind, og `fit_guess` bliver til `fit`.

## Bureauer

- **AFP** – det franske nyhedsbureaus egne linjer (på france24.com): overskrifter, der siger nyheden ("Alle kandidater til FN's generalsekretær fik veto"), omkring 100 om dagen og ofte først. Radaren har ingen AFP i dag. (1,15)
- **Reuters, seneste time** – et tillæg til den Reuters, der allerede følges. Google News giver højst 100 historier pr. søgning, og Reuters skriver langt flere. Derfor kommer de friske for sent eller slet ikke: af den sidste times 7 var kun 2 med. En søgning på den seneste time, hentet hvert 5. minut, fanger næsten alle og tæller som samme medie. (1,1)
- **AP, seneste time** – samme forbedring for AP; halvdelen af den sidste times historier manglede. (1,1)
- **Al Arabiya** (Telegram) – Saudi-lejrens hurtige linjer, ligesom Al Jazeeras hastelinjer for Qatar ("Putins udsending: Rusland og USA annoncerer snart nye fælles initiativer"). Omkring 80 om dagen, bekræftet kanal. (1,1)
- **Axios** – korte, oplysende overskrifter og ofte først med USA's beslutninger og diplomatiet i Mellemøsten ("Iran-støttede militser sender penge tilbage til Revolutionsgarden, siger USA"). Omkring 15 om dagen. (1,1)
- **Qatar News Agency** – Qatars egen stemme: emiren, premier- og udenrigsministeren ("Qatar bekræfter fortsat støtte til Libanon"). Omkring 15 om dagen; Qatar-lejren har ellers kun Al Jazeera. (1,0)
- **WAM** – Emiraternes statsbureau. Meget støj (festivaler og ceremonier, omkring 60 om dagen), men den eneste emiratiske officielle stemme. (0,6)
- **Egyptens statsinformationstjeneste (SIS)** – styret i Kairo med egne ord ("Egyptens og Sudans udenrigsministre afviser forsøg på at skade forholdet"). Omkring 12 om dagen. (0,9)
- **Petra** – Jordans statsbureau og en ny lejr: kongens og regeringens holdninger. Omkring 13 om dagen. (0,8)
- **Iraqi News Agency** – Iraks statsbureau, omkring 25 om dagen. Mange titler ender på "» Iraqi News Agency", derfor lavere. (0,7)
- **SANA** (Telegram) – Syriens statsbureau: den nye regerings handlinger og ministrenes udtalelser. Omkring 80 om dagen; bureauets egne feeds er stoppet eller kan ikke læses. (0,8)
- **Saba** – bureauet for Yemens anerkendte regering (ikke houthiernes). En ny lejr, nu hvor krigen mellem houthierne og Saudi-Arabien er en hovedhistorie. Omkring 6 om dagen. (0,9)
- **Oman News Agency** – Omans stemme og en ny lejr; Oman mægler mellem Washington og Teheran. Ujævnt tempo (55 på tre dage). (0,7)
- **Algérie Presse Service** – Algeriets statsbureau og en ny lejr: præsident Tebbounes handlinger og statens linje over for Marokko og Frankrig. Omkring 25 om dagen, en del kultur. (0,6)
- **Bernama** – Malaysias statsbureau og en ny lejr. Lav prioritet: omkring 85 om dagen, mest indenrigs. (0,5)

## Regeringer

- **Storbritanniens premierminister** – Downing Streets egne meddelelser: samtaler, møder og udtalelser, fx mødet med Zelenskyj. 1-2 om dagen, halvdelen indenrigs. Udenrigsministeriet følges, premierministeren ikke. (1,0)
- **USA's finansministerium** – den førende stats sanktioner, når de kommer ("Operation Economic Outcast rammer Irans finansielle netværk"). 1-2 om dagen. (1,1)
- **Pentagon** – USA's forsvarsministerium, nu kaldet krigsministeriet: referater af møder og beslutninger, fx Hegseths møde med den britiske forsvarsminister. Omkring 5 om ugen. Siden har et værn mod robotter; bliver radaren afvist, skal viceværten slå kilden fra. (1,0)
- **USA's FN-mission** – USA's ord i Sikkerhedsrådet, omkring én om dagen. Titlen siger kun hvor; indledningen siger hvad. (0,8)
- **Frankrigs udenrigsministerium** – en stormagts udenrigsministerium ("Irans chargé d'affaires indkaldt i Frankrig"). Omkring 5 om dagen. Ministeriets eget feed afviser radaren, og vejen gennem Google News tager ambassadesider med. (0,7)
- **Kinas udenrigsministerium** – Beijings egen gengivelse af Wang Yis møder og udtalelser, omkring 5 om dagen. Nogle titler har ministeriets navn hængende på. (0,8)
- **Tyrkiets udenrigsministerium** (to feeds, ét medie) – Ankaras nummererede udtalelser, fx om Iraks nye ministre og fælles udtalelser fra de muslimske landes udenrigsministre. Plus Hakan Fidans møder, fx med Hamas' politiske leder. 2-4 om dagen tilsammen. (1,0 og 0,9)
- **Syriens præsidentembede** (Telegram) – al-Sharaas møder, samtaler og aftaler, nogle få om ugen. Bekræftet kanal. (1,0)
- **Den Islamiske Samarbejdsorganisation (OIC)** – de muslimske landes herskere samlet, fx udenrigsministerrådet i Bagdad i disse dage. Omkring én om dagen. (0,8)
- **Golfstaternes Samarbejdsråd (GCC)** – Golfherskernes fælles udtalelser, omkring 3 om dagen. (0,7)

## Danmark

- **Statsministeriet** – statsministerens egne pressemeddelelser ("Aftale mellem Grønland, Danmark og USA", "Udtalelse fra statsminister Mette Frederiksen"). Omkring 3 om måneden, og hver er vigtig; den seneste var 22. september. Ulempe: feedet er hele arkivet, ca. 1 MB hver gang radaren henter. (1,2)
- **Udenrigsministeriet** – ministeriets pressemeddelelser gennem Via Ritzau. Det er den liste, um.dk selv viser: dansk udenrigspolitik fra første hånd, omkring 3 om ugen. (1,0)
- **Udlændinge- og Integrationsministeriet** – gruppens danske kerneemne fra første hånd. Fx "Regeringen vil indføre screeningsmodel for ansøgere til dansk statsborgerskab" og "Bødskov: Ekstrem islamisme og æresrelateret vold …". Omkring 2 om ugen. (1,3)
- **Justitsministeriet** – PET, grænsekontrol og love, der rører religion (fx koranloven), omkring 2 om ugen. Lidt dyrevelfærd og flagdage. (0,9)

## Lejre radaren mangler

- **Naharnet** – Libanon og en ny lejr. Overskrifter som et nyhedsbureaus ("Rubio beder Aoun ikke give beslaglagte sprængstoffer tilbage til Hizbollah"), omkring 25 om dagen. (0,9)
- **Rudaw** – Kurdistan-regionens blik på Irak, Iran, Syrien og Tyrkiet ("Irak anslår tabet fra krigen mellem USA og Iran til 60 mia. dollar"). Omkring 12 om dagen. (0,8)
- **Kyiv Independent** – Ukraines side af krigen i Europa med oplysende overskrifter, omkring 15 om dagen. Bedre end statsbureauet Ukrinform, som har mere lokalt småstof. (0,9)
- **Libya Herald** – Libyen: centralbanken, olieindtægterne og de rivaliserende regeringer, omkring 7 om dagen. (0,7)
- **Dabanga** – krigen i Sudan, fortalt af en uafhængig sudanesisk redaktion, omkring 2 om dagen. (0,7)
- **Yonhap** – Koreas nyhedsbureau. Lav prioritet: Fjernøsten har kun kinesiske statskilder, men omkring 70 om dagen, mest koreansk indenrigs. (0,6)

## Prøvet, men ikke foreslået

**Kan ikke følges af radaren**

- **Folketinget:** ft.dk afviser automatiske opslag, og Folketingets rum hos Via Ritzau er fra 2007.
- **TV 2 Politik og TV 2 Udland:** har intet eget feed; TV 2's samlede feed følges allerede.
- **Ritzau's nyhedsbureau:** har intet offentligt feed. Via Ritzaus fælles feed er pressemeddelelser fra firmaer og organisationer, altså støj.
- **Forsvarsministeriet:** feedet er forkert kodet, så radaren kan ikke læse det, og der er få nyheder.
- **Partierne:** Danmarksdemokraternes feed stoppede i november 2025. V, LA, K og M skriver få og sjældent om vores emner. DF, Borgernes Parti og Enhedslisten afviser opslag. S, SF, RV og Alternativet har intet feed.
- **AP's og Reuters' egne feeds:** findes ikke, eller ligger bag en mur mod robotter.
- **Afviser radaren eller svarer ikke:** Al Arabiyas og Arab News' websider, MAP (Marokko), KUNA (Kuwait), BNA (Bahrain), Jordan Times, Morocco World News, Sudan Tribune, SUNA (Sudan), Pakistans militær (ISPR), Irans præsident og Kazinform (Kasakhstan).
- **Feeds der er stoppet, tomme eller ikke kan læses:** SANA's RSS (stoppet 29/9), INA's RSS (stoppet i maj), OFAC's gamle feed (stoppet februar 2025), CENTCOM (tomme feeds), MENA (Egypten), Egyptens præsident og Naharnets, Rudaws og L'Orient Todays egne feeds. Naharnet og Rudaw følges derfor gennem Google News.
- **Sider der sender radaren i ring:** Irans udenrigsministerium, Khamenei.ir og Tyrkiets præsident; via Google News giver Tyrkiets præsident kun tomme titler.
- **Certifikatfejl:** Pakistans udenrigsministerium og premierministerens kontor.
- **Mest stillingsopslag, dokumenter og forskning via Google News:** NATO, EU's udenrigstjeneste, EU's Ministerråd, IAEA og Pentagons websted (derfor dets eget feed i stedet).
- **Telegram:** Sky News Arabia, Middle East Eye og Irans udenrigsministerium har ingen aktiv offentlig kanal.

**Virker, men fravalgt**

- **Al Hadath:** samme linjer som Al Arabiya.
- **Asharq News:** lange første-sætninger som overskrift; Saudi-lejren får Al Arabiya i stedet.
- **"الحدث عاجل", Al Qahera News og WAFA på Telegram:** ikke bekræftede kanaler; Al Qaheras linjer ender i kolon, før udsagnet kommer.
- **Anadolu (arabisk) og TRT Arabi på Telegram:** Tyrkiet har allerede tre kilder.
- **Hærens kanal i Israel (IDF):** virker, men den israelske lejr har Jerusalem Post og Times of Israel, som gengiver hærens udmeldinger. Jeg foreslår den ikke uden ejerens ja.
- **Regeringen.dk:** overlapper Statsministeriet og ministerierne og fylder 1 MB pr. hentning.
- **Undervisningsministeriet:** virker, men er sjældent relevant.
- **Altinget Christiansborg:** mest kommentarer; Altingets samlede feed følges allerede.
- **TAP (Tunesien), AZERTAC, Ukrinform, Kuwait Times, Times of Oman, Gulf News, Saudi Gazette, Arab News, SCMP, Euronews, Politico, The Hill, Malay Mail, Express Tribune, Geo, Amu TV, Eurasianet, Hespress, Japan Times, Tehran Times, Mehr og ISNA:** virker for det meste. Men de er mest lokalstof, har spørgsmåls- eller tomme titler, eller lejren er allerede dækket. ISNA er det bedste alternativ, hvis IRNA vejes ned.
- **Avisen.dk og Via Ritzaus fælles feed:** lette nyheder og pressemeddelelser.

**Udelukket efter reglerne**

- **Russiske medier på EU's liste:** RT, RT Arabic, Sputnik, RIA Novosti, Izvestija, Rossijskaja Gazeta og de øvrige.
- **Iran:** Press TV og statsradioen IRIB's kanaler, også Al-Alam, står på EU's Iran-liste fra 2022.
- **Terrorlistede gruppers kanaler:** Hamas og al-Qassam, Hizbollah (al-Manar) og houthierne (al-Masirah og det houthi-styrede saba.ye).
- **Bevægelsens egne medier:** følges allerede for sig.
- **Facebook, X, Instagram og TikTok.**
- **Tjekket:** SANA står ikke på EU's lister (søgt i OpenSanctions). TASS, som følges i dag, var med i et udkast til EU's 16. sanktionspakke, men kom ikke med i den vedtagne. 2026-pakkerne har jeg ikke kunnet efterprøve, så det er værd at tjekke.
