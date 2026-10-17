"""The issues' leads in the wiki, newest first (the review of 2026-10-17: 'the newest answer governs' must hold in the
first sentence a reader and the editor's brain see). Each lead's first sentence carries the newest answer that reads
the issue, with its day; the history behind it stays whole on the page as 'history_da'. Every sentence is the
history's own reading (public/viden/movement.json 'issues'), reordered and attributed – never Khabar's own words.

scripts/build_begreber.py uses SAG_LEAD for the issue pages; its check fails when an issue's newest main answer is newer
than the lead, so a new answer on an issue means a new lead here."""

SAG_LEAD = {
    'afghanistan-pakistan':
        "Ifølge Hizb ut-Tahrirs svar af 18/8/2026 bruges Pakistan i 2026 over for Iran og i Mekka-aftalen, og ifølge "
        "svarene af 2022-2024 skifter hæren Pakistans politikere ud. Efter Talibans magtovertagelse 15/8/2021 læser "
        "svarene af 28/1/2023 og 27/8/2024 grænsesammenstødene som drevet af USA: Pakistans hær bindes vestpå, så "
        "Indien kan vende sig mod Kina, og Taliban presses til underkastelse.",
    'afrika':
        "Ifølge Hizb ut-Tahrirs svar af 13/3/2023 går Nigeria over til den britiske side med Tinubu, og svarene om Kenya, "
        "Nigeria, Tanzania og Gambia (2012-2023) ser Storbritannien holde fast. Hizb ut-Tahrirs svar fra 2004 til 2024 "
        "læser Afrika som en kampplads, hvor USA som den nye kolonimagt søger at fortrænge Storbritannien og Frankrig fra "
        "deres gamle kolonier gennem kup, valg, ICC, IMF, »terrorbekæmpelse« og regionale organisationer, mens de "
        "europæiske magter forsvarer sig gennem de politiske klasser, ECOWAS, SADC, Frankofonien og Commonwealth.",
    'afrikas-horn':
        "Ifølge Hizb ut-Tahrirs svar af 21/11/2021 skiftede USA plan under Biden fra at støtte felttoget i Tigray til at "
        "føre Etiopien mod opdeling. Svaret af 15/10/2018 læste forsoningen mellem Etiopien og Eritrea som USA's og "
        "Saudi-Arabiens værk for at samle Hornets stater mod Europa og Kina, og ifølge svaret af 28/11/2008 vil USA "
        "kontrollere Hornet og Bab el-Mandeb fra havet, mens Frankrig holder fast i Djibouti.",
    'centralasien':
        "Ifølge Hizb ut-Tahrirs svar af 15/1/2022 var CSTO's første indgreb i Kasakhstan Ruslands forsøg på at fastholde "
        "sit vigtigste land efter Ukraine, og det afslørede nye russiske svagheder. Svaret af 18/10/2020 ser Kirgisistan "
        "fast i Ruslands greb og svaret af 6/9/2015 Usbekistan knyttet til USA som afsæt mod Rusland og Kina. Ifølge "
        "svaret af 19/9/2009 er Centralasien en vital interesse for både Rusland og USA, og kampen mellem dem blusser op "
        "igen og igen.",
    'den-internationale-tilstand':
        "Ifølge Hizb ut-Tahrirs svar af 12/6/2026 er Rusland nu en mellemmagt – gået fra at ville anerkendes som "
        "medstyrende stormagt (28/10/2010) over rollen som USA's redskab i Syrien (2015-2021). Svaret af 14/1/2026 læser "
        "USA som den førende stat, hvis strategier siden Anden Verdenskrig alle har haft samme mål: at forhindre en "
        "rival. Kina er ifølge svaret af 22/11/2025 en uafhængig regional stormagt, der ikke udfordrer USA globalt, og "
        "Europa er ifølge svarene splittet og blev samlet under USA af Ukraine-krigen (2/10/2022).",
    'det-indiske-subkontinent':
        "Ifølge Hizb ut-Tahrirs svar af 15/5/2025 bruger USA Indien under Modi til at omringe Kina og vil derfor fjerne "
        "Indiens problemer med Pakistan – Kashmir, vandet og de militante bevægelser – så Indien kan vende sine styrker "
        "mod Kina. Svaret af 17/9/2024 ser USA have fået overtaget i Indien og Pakistan, og Kina har ifølge svarene "
        "økonomiske interesser i regionen (CPEC, Myanmar), men ingen politisk indflydelse i dens stater.",
    'egypten':
        "Ifølge Hizb ut-Tahrirs svar af 28/6/2026 er Egypten eksemplet på en underordnet stat i modsætning til "
        "satellitstaterne. Under Sisi er Egypten ifølge svarene af 2015-2026 USA's kanal i Libyen (Haftar), i Yemen, i "
        "Sudan (hæren og Kvartetten) og over for Gaza, og svarene har i hele perioden 2004-2026 læst Egypten som den "
        "vigtigste bastion for USA's indflydelse i regionen, hvor hæren er nøglen.",
    'europa':
        "Ifølge Hizb ut-Tahrirs svar af 14/1/2026 afpresser USA de allierede (5 % af BNP), og svaret af 12/11/2025 læser "
        "en plan om at overtage Storbritanniens indflydelse på Cypern. Vendepunktet er krigen i Ukraine: ifølge svarene "
        "af 2022-2023 trak USA Europa under sin ledelse, bandt det til amerikansk gas og slog Frankrigs forsøg på en "
        "uafhængig europæisk styrke ned (18/7/2023), mens USA og Storbritannien skubber Tyskland til at opruste mod "
        "Rusland (23/6/2023).",
    'fjernosten':
        "Ifølge Hizb ut-Tahrirs svar af 1/5/2026 er MDCP-aftalen med Indonesien et led i USA's opbygning mod Kina, og "
        "svaret af 22/11/2025 læser Kina som en regionalmagt, der kun reagerer på USA's træk. Ifølge svaret af 30/3/2021 "
        "er inddæmningen under Biden afløst af konfrontation: AUKUS (25/9/2021), Japans genoprustning som hjørnesten "
        "(24/12/2022) og NATO's rækkevidde mod Kina.",
    'fn-og-folkeretten':
        "Ifølge Hizb ut-Tahrirs svar af 7/4/2021 vandt USA over Storbritannien i Libyen gennem FN's dialogforum, og FN og "
        "de internationale domstole er ifølge svarene redskaber, som magterne bruger mod hinanden. Svaret af 9/4/2016 "
        "ser USA's atomtopmøder sigte mod at nedruste andre, og svaret af 13/3/2012 så USA bruge Den Internationale "
        "Straffedomstol i Kenya, som Frankrig og Storbritannien ifølge svaret af 25/10/2008 brugte mod USA i Sudan.",
    'golfen':
        "Ifølge Hizb ut-Tahrirs svar af 18/8/2026 er trepartsalliancen USA's redskab til pres på Iran, og svaret af "
        "5/8/2026 ser Storbritannien reduceret til Golfstaterne og Jordan. Hizb ut-Tahrirs svar læser Golfen som en "
        "arena, hvor USA siden 1970'erne har afløst Storbritannien, og hvor den britiske indflydelse lever videre i de "
        "små Golfstater (Emiraterne, Qatar, Kuwait, Bahrain, Oman). Vendepunktet er ifølge svarene kong Abdullahs død i "
        "januar 2015: Saudi-Arabien gik fra britisk-loyalt til underordnet under USA.",
    'irak':
        "Ifølge Hizb ut-Tahrirs svar af 5/8/2026 afvikles Irans tildelte rolle i Irak som led i planen om et underordnet "
        "Iran: veto mod Maliki, al-Zaidi indsat, afvæbningsfrist 30/9/2026, antikorruptionskampagne og angreb på PMF. "
        "Hizb ut-Tahrirs svar læser Irak som under amerikansk kontrol siden besættelsen i 2003, og efter "
        "tilbagetrækningen i 2011 holdes indflydelsen gennem ambassaden, baserne og rammeaftalen fra 2008.",
    'iran':
        "Ifølge Hizb ut-Tahrirs svar af 18/8/2026 og 27/9/2026 er forhandlingerne fastlåst, og USA presser Iran med "
        "trepartsalliancen og lokker med Yemen. Ifølge svaret af 28/6/2026 fik den politiske fløj overtaget, og Iran "
        "vender tilbage som satellit, hvilket USA accepterer som minimumsmål. Det reviderede svaret af 3/6/2026, der så "
        "Revolutionsgarden ved roret og Iran på vej mod uafhængighed efter krigen, som USA ifølge svaret af 4/4/2026 "
        "indledte 28/2/2026 for at gøre Iran underordnet.",
    'jordan':
        "Ifølge Hizb ut-Tahrirs svar af 5/8/2026 er Jordan en af Storbritanniens sidste rester uden magt til at modsætte "
        "sig USA, og svaret af 28/1/2025 regner kongen blandt USA's tilhængere under presset om Gazas befolkning. Svaret "
        "af 6/6/2022 læser økonomien som en underordnet del af den amerikanske (dinar, Fed, IMF) og importen af vand og "
        "gas fra Israel som bevidst afhængighed.",
    'kashmir':
        "Ifølge Hizb ut-Tahrirs svar af 15/5/2025 standsede USA krigen 10/5/2025 og vil nå sine mål – Kashmir, vandet og "
        "bevægelserne – gennem forhandling. Ifølge svaret af 3/1/2024 accepterede Pakistans hærledelse stiltiende "
        "annekteringen, som Modi-regeringen ifølge svaret af 18/8/2019 gennemførte 5/8/2019 med USA's grønne lys.",
    'kaukasus':
        "Ifølge Hizb ut-Tahrirs svar af 16/8/2025 er fredsaftalen i Washington og »Trump-ruten« – en korridor lejet til "
        "USA i 100 år – vejen til at styrke USA i Aserbajdsjan, udvide det i Armenien og fjerne Ruslands indflydelse. "
        "Krigen i 2020 og generobringen af Karabakh 19–20/9/2023 læses i svarene som amerikanske træk gennem Erdoğans "
        "Tyrkiet, mens Rusland var bundet i Ukraine.",
    'kina-taiwan':
        "Ifølge Hizb ut-Tahrirs svar af 1/5/2026 ligger Taiwan-scenariet bag USA's aftale med Indonesien. Svaret af "
        "3/7/2023 læser USA's behandling af Taiwan som de facto anerkendelse uden formel anerkendelse, og fra 2021 læser "
        "svarene en skarpere linje: bevæbning og politisk støtte (30/3/2021) og provokation, der skal stille Kina mellem "
        "at fremstå svagt og blive trukket ind i en sump (23/8/2022, 31/10/2022).",
    'libanon':
        "Ifølge Hizb ut-Tahrirs svar af 2/5/2026 er de direkte forhandlinger med Israel fra 14/4/2026 Libanons indtræden i "
        "normaliseringen under fortsatte israelske angreb og bufferzoner. Vendepunktet er ifølge svaret af 23/1/2025 "
        "valget af Joseph Aoun og Nawaf Salam: USA skubber Iran og Hizbollah ud og overdrager sagen til Saudi-Arabien. "
        "Ifølge svaret af 9/5/2008 har USA haft indflydelsen i Libanon siden Taif.",
    'nordafrika':
        "Ifølge Hizb ut-Tahrirs svar af 28/11/2022 skiftede Tunesien med Kais Saied fra britisk til fransk indflydelse, "
        "som også svaret af 1/8/2021 læste, og Algeriet og Marokko læses frem til da som britisk-loyale styrer, hvis "
        "indbyrdes spænding er rollefordelt (18/12/2021). Libyen blev fra 2014 hovedarenaen: Haftar og Tobruk på USA's "
        "side, Tripoli på Europas, indtil svaret af 7/4/2021 så USA vinde runden gennem FN's dialogforum.",
    'palaestina':
        "Ifølge Hizb ut-Tahrirs svar af 2/5/2026 og 2/9/2025 betyder tostatsløsningen nu et demilitariseret selvstyre "
        "under israelsk dominans, og normaliseringen udvides (Saudi-Arabien, Syrien, Libanon) med Israel som regional "
        "forvalter. Under Gaza-krigen så svarene af 22/3/2024 og 4/9/2024 USA som den, der reelt fører krigen, og "
        "Netanyahus »dagen efter« (Gaza adskilt og demilitariseret) som det mest sandsynlige. Palæstina-sagen er ifølge "
        "svarene et amerikansk projekt siden Eisenhower (1959), og fra 2018 læses normaliseringen mellem Israel og "
        "herskerne som USA's hovedvej.",
    'sudan':
        "Ifølge Hizb ut-Tahrirs svar af 29/7/2026 og 3/11/2025 overgav hæren El Fasher efter en beslutning i Washington, "
        "og fra svaret af 6/2/2025 er udskillelsen af Darfur under RSF USA's plan. Siden 19/3/2023 er både hæren og RSF "
        "ifølge svarene USA's redskaber.",
    'sydoestasien':
        "Ifølge Hizb ut-Tahrirs svar af 1/5/2026 skal MDCP-aftalen fra 13/4/2026 give USA større kontrol med "
        "Malaccastrædet, hvor det meste af Kinas olie og gas passerer, og Indonesien læses gennemgående som underordnet "
        "USA (20/9/2012, 11/11/2024, 1/5/2026). Hizb ut-Tahrirs svar læser Sydøstasien som en arena både for "
        "inddæmningen af Kina og for den britisk-amerikanske rivalisering: Myanmars hær som loyal over for Storbritannien "
        "(26/6/2012, 6/3/2021) og Malaysia som under britisk politisk kontrol (26/5/2018).",
    'syrien':
        "Ifølge Hizb ut-Tahrirs svar af 27/1/2026 og 26/7/2025 er al-Sharaa-regeringen USA's nye redskab, der afvikler "
        "SDF og forhandler med Israel om en demilitariseret sydzone – planen uændret, redskabet skiftet. Svaret af "
        "8/12/2024 ser Tyrkiet, med USA bag sig, sætte offensiven i gang, der væltede Assad, og ifølge svarene har den "
        "reelle indflydelse i Syrien været amerikansk siden Hafez al-Assad.",
    'tyrkiet':
        "Ifølge Hizb ut-Tahrirs svar af 18/8/2026 er Tyrkiet med i Mekka-aftalen, og svaret af 12/11/2025 slår fast, at "
        "Tyrkiet er flyttet fra den britiske til den amerikanske lejr. Fra 2008 kalder svarene Erdoğan-regeringen "
        "underordnet USA eller en satellit i USA's bane, brugt som regionalt redskab i Syrien, Libyen, Kaukasus, på "
        "Cypern og i Afghanistan.",
    'ukraine-rusland':
        "Ifølge Hizb ut-Tahrirs svar af 12/6/2026 er Rusland en mellemmagt, og Ukraines dybe angreb er tilskyndet af "
        "Vesten og især USA. Ifølge svaret af 19/8/2025 skiftede USA middel: krigen køles ned mod en våbenhvile, den "
        "endelige løsning skydes år ud, og Rusland skal skilles fra Kina. Fra 22/12/2021 og 4/3/2022 læser svarene "
        "krigen som en fælde, USA lokkede Rusland i for at binde det, samle Europa og fjerne Rusland fra stormagternes "
        "kreds.",
    'usa-europa':
        "Ifølge Hizb ut-Tahrirs svar af 2/5/2025 udelukker USA igen europæerne, nu fra Iran-sagen. Ukraine-krigen "
        "samlede ifølge svarene af 2/10/2022 og 1/3/2023 Europa under amerikansk lederskab, og forholdet mellem USA og "
        "Europa er ifølge svarene en rivalisering inden for den vestlige lejr.",
    'yemen':
        "Ifølge Hizb ut-Tahrirs svar af 27/9/2026 var houthiernes erobring af vestkysten en amerikansk plan for at fjerne "
        "de sidste britiske tilhængere, og ifølge svaret af 11/1/2026 skiftede Rashad al-Alimi fra britisk side til "
        "Saudi-Arabien, mens USA skubbede Riyadh til at tage Hadramawt. Hizb ut-Tahrirs svar læser Yemen som en "
        "kampplads mellem Storbritannien og USA siden 1960'erne.",
}
