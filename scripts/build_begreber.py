"""Build Khabar's wiki of concepts: public/viden/begreber.json (the pages) and the app's small linker index
public/viden/begreber-index.json. One page per state, power, group and issue that Hizb ut-Tahrir's political answers
read, compiled only from the movement layer (public/viden/movement.json, built by scripts/build_movement.py) – never a
word of Khabar's own analysis. Every text is the movement's reading as the layer holds it, attributed ('Ifølge Hizb
ut-Tahrirs svar af d/m/åååå …'), and the newest answer governs the lead.

Pages
  stat · magt · gruppe · organisation   every subject the layer holds readings or a current reading for (the subject
                                        ids without '--'), and a party that only a relation names (Finland); the
                                        name from docs/hjerne/knowledge-v0.json (powers, actors, states) unless
                                        NAMES gives the reader's own (Israel, Yemen) or the model has none
      lead_da      the current reading (movement.json 'current': the newest answer governs, reconciled by
                   build_movement); without one, the newest reading; a party of a relation only: that relation
      timeline     every reading of the subject, newest first, each naming its day (a reading over several answers
                   gets their span: 'Ifølge Hizb ut-Tahrirs svar fra 12/3/2016 til 29/7/2018 …'); a reading two
                   syntheses drew from one answer once
      relations    each relation ('a--b' subject) on both parties' pages: its current reading, else its newest
      answers      every answer that touches it – tagged with it in movement-index.json (states, powers) or behind
                   one of its readings or relations – newest first
      related      the issues named after it ('Iran-sagen'), the other parties of its relations (newest first), then
                   the issues that link it (most shared answers first); a page no issue links: the one or two
                   issues its answers are tagged with most
  sag                                   every issue with a history (movement.json 'issues'); an issue whose id is a
                                        state's ('iran') gets the page id '<id>-sagen' ('Iran-sagen')
      lead_da      the history's opening sentence and its newest three sentences (LEAD_PICK where that would drop a
                   power's newest reading)
      timeline     the notes of the answers the history rests on (the issue's 'nrs'), newest first
      answers      the answers tagged with the issue or behind its history, newest first
      related      the pages it is named after, the states, powers, groups and issues its history names and the
                   groups whose readings rest on its answers (the most central first), and the issues above or below
                   it in docs/hjerne/knowledge-v0.json
  'subject' is the page's id in the layer: a key of movement.json 'readings'/'current', or of 'issues' for a sag.
  'lead_nr'/'lead_date' are the answer the lead rests on: the current reading's, or for a sag the newest answer the
  lead names by its day.

Then the abstract concepts of docs/hjerne/begreber-ideer.json (written by another part of the work, in the same schema)
are merged when the file is there: on an id or alias clash the concept's own entry wins and the clash is reported, a
concept with a broken rule is left out and reported, and a page the concept names as related links back to it.

Aliases are the Danish forms Danish news uses, written here by hand (ALIASES, ISSUE_ALIASES): a proper name is
case-sensitive; never an adjective or a word for a people ('amerikansk', 'russerne'), so a link always names a state,
power, group or issue; never an ordinary Danish word (STOPWORDS); never in two pages. The base form only: the linker
adds the possessive itself (Irans, USA's, Hamas'), and the longest alias wins ('krigen i Ukraine' over 'Ukraine').

    py scripts/build_begreber.py     -> public/viden/begreber.json and public/viden/begreber-index.json
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_movement as bm  # noqa: E402
from begreber_leads import SAG_LEAD  # noqa: E402 – the issues' leads, newest first

VIDEN = ROOT / 'public' / 'viden'
LAYER = VIDEN / 'movement.json'
MINDEX = VIDEN / 'movement-index.json'
SEED = ROOT / 'docs' / 'hjerne' / 'knowledge-v0.json'
IDEAS = ROOT / 'docs' / 'hjerne' / 'begreber-ideer.json'
OUT = VIDEN / 'begreber.json'
OUT_INDEX = VIDEN / 'begreber-index.json'

KINDS = ('stat', 'magt', 'gruppe', 'sag', 'begreb', 'aftale', 'sted', 'organisation', 'proces')
FIELDS = ('id', 'name', 'kind', 'aliases', 'case_sensitive', 'lead_da', 'lead_nr', 'lead_date', 'timeline', 'relations',
          'answers', 'related', 'subject', 'history_da')
ID = re.compile(r'^[a-z0-9][a-z0-9-]{1,60}$')
LEAD_SENTENCES = 4

# ---------------------------------------------------------------------------------------------- names and kinds

# the reader's name where the seed model's is a description ('Den israelske stat', 'Yemen (den anerkendte regering)')
NAMES = {'israel': 'Israel', 'yemen': 'Yemen'}
# subjects the seed model does not name
EXTRA_NAMES = {'australien': 'Australien', 'brasilien': 'Brasilien', 'brunei': 'Brunei', 'filippinerne': 'Filippinerne',
               'finland': 'Finland', 'gabon': 'Gabon', 'georgien': 'Georgien', 'guinea': 'Guinea', 'kenya': 'Kenya',
               'kosovo': 'Kosovo', 'mauretanien': 'Mauretanien', 'serbien': 'Serbien', 'sverige': 'Sverige'}
# not states: the armed and political groups, the alliance, and the authority the answers say is no state
KIND = {'hamas': 'gruppe', 'hizbollah': 'gruppe', 'houthierne': 'gruppe', 'rsf': 'gruppe', 'nato': 'organisation',
        'palaestinensisk-selvstyre': 'organisation'}

# the Danish forms Danish news uses (DR, TV 2, Ritzau, the papers); base forms only
ALIASES = {
    'afghanistan': ['Afghanistan'],
    'algeriet': ['Algeriet'],
    'armenien': ['Armenien'],
    'aserbajdsjan': ['Aserbajdsjan', 'Azerbaijan'],
    'australien': ['Australien'],
    'bahrain': ['Bahrain'],
    'bangladesh': ['Bangladesh'],
    'belarus': ['Belarus', 'Hviderusland'],
    'brasilien': ['Brasilien'],
    'brunei': ['Brunei'],
    'burkina-faso': ['Burkina Faso'],
    'canada': ['Canada'],
    'cypern': ['Cypern'],
    'danmark': ['Danmark'],
    'egypten': ['Egypten'],
    'emiraterne': ['De Forenede Arabiske Emirater', 'Forenede Arabiske Emirater', 'Emiraterne', 'UAE'],
    'eritrea': ['Eritrea'],
    'etiopien': ['Etiopien'],
    'eu': ['EU', 'Den Europæiske Union', 'Europæiske Union'],
    'filippinerne': ['Filippinerne'],
    'finland': ['Finland'],
    'frankrig': ['Frankrig'],
    'gabon': ['Gabon'],
    'georgien': ['Georgien'],
    'graekenland': ['Grækenland'],
    'guinea': ['Guinea'],
    'hamas': ['Hamas'],
    'hizbollah': ['Hizbollah', 'Hizbullah', 'Hezbollah'],
    'houthierne': ['houthierne', 'houthi-oprørerne', 'houthioprørerne', 'houthi-bevægelsen', 'houthibevægelsen',
                   'houthi-militsen', 'houthimilitsen', 'Ansar Allah', 'houthi', 'houthis'],   # the last two: the machine's Danish
    'indien': ['Indien'],
    'indonesien': ['Indonesien'],
    'irak': ['Irak'],
    'iran': ['Iran', 'Den Islamiske Republik Iran'],
    'israel': ['Israel', 'Staten Israel'],
    'japan': ['Japan'],
    'jordan': ['Jordan'],
    'kasakhstan': ['Kasakhstan', 'Kazakhstan'],
    'kenya': ['Kenya'],
    'kina': ['Kina', 'Folkerepublikken Kina'],
    'kirgisistan': ['Kirgisistan', 'Kirgisien'],
    'kosovo': ['Kosovo'],
    'kuwait': ['Kuwait'],
    'libanon': ['Libanon'],
    'libyen': ['Libyen'],
    'malaysia': ['Malaysia'],
    'mali': ['Mali'],
    'marokko': ['Marokko'],
    'mauretanien': ['Mauretanien'],
    'myanmar': ['Myanmar', 'Burma'],
    'nato': ['Nato', 'NATO'],
    'niger': ['Niger'],
    'nigeria': ['Nigeria'],
    'nordkorea': ['Nordkorea', 'Nord-Korea'],
    'oman': ['Oman'],
    'pakistan': ['Pakistan'],
    'palaestinensisk-selvstyre': ['Det Palæstinensiske Selvstyre', 'Palæstinensiske Selvstyre',
                                  'Den Palæstinensiske Myndighed', 'Palæstinensiske Myndighed'],
    'polen': ['Polen'],
    'qatar': ['Qatar'],
    'rsf': ['RSF', 'Rapid Support Forces'],
    'rusland': ['Rusland', 'Den Russiske Føderation'],
    'saudi-arabien': ['Saudi-Arabien', 'Saudiarabien'],
    'serbien': ['Serbien'],
    'somalia': ['Somalia'],
    'storbritannien': ['Storbritannien', 'Det Forenede Kongerige'],
    'sudan': ['Sudan'],
    'sverige': ['Sverige'],
    'sydkorea': ['Sydkorea', 'Syd-Korea'],
    'sydsudan': ['Sydsudan', 'Syd-Sudan'],
    'syrien': ['Syrien'],
    'tadsjikistan': ['Tadsjikistan', 'Tajikistan'],
    'taiwan': ['Taiwan'],
    'tchad': ['Tchad'],
    'tunesien': ['Tunesien'],
    'turkmenistan': ['Turkmenistan'],
    'tyrkiet': ['Tyrkiet', 'Türkiye'],
    'tyskland': ['Tyskland', 'Forbundsrepublikken Tyskland'],
    'ukraine': ['Ukraine'],
    'usa': ['USA', 'De Forenede Stater', 'Amerikas Forenede Stater'],
    'usbekistan': ['Usbekistan', 'Uzbekistan'],
    'yemen': ['Yemen', 'Jemen'],
}
# written in lower case in Danish news ('houthierne', 'det palæstinensiske selvstyre'): matched in any case
CASE_INSENSITIVE = {'houthierne', 'palaestinensisk-selvstyre'}

# the issues: the page's name, its Danish forms in the news (none where only a state's name would do, or where the
# issue is an idea the concept pages hold), and whether the forms are matched in any case
ISSUE_NAMES = {
    'afghanistan-pakistan': 'Afghanistan og Pakistan', 'afrika': 'Afrika', 'afrikas-horn': 'Afrikas Horn',
    'centralasien': 'Centralasien', 'den-intellektuelle-kamp': 'Den intellektuelle kamp',
    'den-internationale-tilstand': 'Den internationale tilstand', 'det-amerikanske-kontinent': 'Det amerikanske kontinent',
    'det-indiske-subkontinent': 'Det indiske subkontinent',
    'europa': 'Europa', 'fjernosten': 'Fjernøsten', 'fn-og-folkeretten': 'FN og folkeretten', 'golfen': 'Golfen',
    'groenland': 'Grønland', 'kashmir': 'Kashmir', 'kaukasus': 'Kaukasus', 'kina-taiwan': 'Kina og Taiwan',
    'latinamerika': 'Latinamerika', 'nordafrika': 'Nordafrika', 'palaestina': 'Palæstina', 'sahel': 'Sahel',
    'sydoestasien': 'Sydøstasien', 'ukraine-rusland': 'Ukraine og Rusland', 'usa-europa': 'USA og Europa',
    'vesten-danmark': 'Vesten og Danmark',
}
ISSUE_ALIASES = {
    'afrika': ['Afrika'],
    'afrikas-horn': ['Afrikas Horn'],
    'centralasien': ['Centralasien'],
    'det-amerikanske-kontinent': ['den vestlige halvkugle', 'Monroe-doktrinen'],
    'det-indiske-subkontinent': ['det indiske subkontinent'],
    'europa': ['Europa'],
    'fjernosten': ['Fjernøsten'],
    'fn-og-folkeretten': ['FN', 'De Forenede Nationer', "FN's Sikkerhedsråd", 'Sikkerhedsrådet',
                          'Den Internationale Straffedomstol', 'ICC', 'Den Internationale Domstol', 'ICJ'],
    'golfen': ['Golfen', 'Golfstaterne', 'Den Persiske Golf'],
    'groenland': ['Grønland'],
    'iran': ['Iran-krigen', 'krigen mod Iran', 'krigen i Iran'],
    'kashmir': ['Kashmir'],
    'kaukasus': ['Kaukasus', 'Sydkaukasus', 'Nagorno-Karabakh', 'Karabakh'],
    'kina-taiwan': ['Taiwanstrædet', 'Taiwan-strædet', 'Taiwan-spørgsmålet'],
    'latinamerika': ['Latinamerika'],
    'nordafrika': ['Nordafrika', 'Maghreb', 'Vestsahara'],
    'palaestina': ['Palæstina', 'Palæstina-sagen', 'Palæstina-spørgsmålet', 'Palæstina-konflikten'],
    'sahel': ['Sahel', 'Sahel-regionen', 'Sahelregionen'],
    'sudan': ['krigen i Sudan', 'borgerkrigen i Sudan', 'Sudan-krigen', 'Darfur'],
    'sydoestasien': ['Sydøstasien', 'Malaccastrædet'],
    'syrien': ['krigen i Syrien', 'borgerkrigen i Syrien', 'Syrien-krigen'],
    'ukraine-rusland': ['krigen i Ukraine', 'Ukraine-krigen', 'Ukrainekrigen', 'krigen mellem Rusland og Ukraine'],
    'vesten-danmark': ['koranafbrænding', 'koranafbrændingen', 'koranafbrændinger', 'koranafbrændingerne'],
    'yemen': ['krigen i Yemen', 'borgerkrigen i Yemen', 'Yemen-krigen'],
}
ISSUE_CASE_INSENSITIVE = {'det-amerikanske-kontinent', 'det-indiske-subkontinent', 'iran', 'sudan', 'syrien', 'ukraine-rusland',
                          'vesten-danmark', 'yemen'}
# the sentences of a history that make its lead, where the opening and the newest three would leave out a power's
# newest reading: the international situation keeps USA, China, Russia and Europe (its last sentence has no date)
LEAD_PICK = {'den-internationale-tilstand': (0, 1, 2, 3)}
# one answer's reading that holds for several pages the layer did not tag (review 2026-10-17): the answer of 5/8/2026
# reads the Gulf states together as Britain's last remnant – every Gulf state's page carries it
SHARED_READINGS = [('storbritannien', '30093', 'Golfstaterne', ('bahrain', 'emiraterne', 'kuwait', 'oman', 'qatar'))]
# a timeline row on the wrong page: the answer of 14/1/2026 (the USA's security strategies) on the Palestine issue
ROW_EXCLUDE = {'palaestina': {'28942'}}
# a power's lead is its standing as a power (the answer that reads it as one); its newer rows are its acts in one arena
LEAD_IS_STANDING = {'magt'}

# -------------------------------------------------------------------------------------------------- alias rules

# ordinary Danish words a link must never be (the alias rule and the test's stoplist): the function words, everyday
# nouns, verbs and adjectives, the words of politics and war, and the adjectives and words for peoples
FUNCTION_WORDS = frozenset("""
af alle allerede alligevel alt altid anden andet andre at bag bagefter bare begge blandt bort både da de dem den denne
dens der deres derfor derefter dermed desuden det dette dig din dine disse dit dog du efter eftersom egen eget egne
eller ellers en end endda endnu ene eneste enhver ens enten er et ethvert fem fire flere flest fleste for foran fordi
forbi fra frem først første gennem godt ham han hans hele helt hende hendes her heller hen hinanden hos hun hvad hvem
hver hvert hvilke hvilken hvilket hvis hvor hvordan hvorfor hvornår i igen ikke ind inde indtil ingen intet ja jeg jer
jeres kun lidt lige man mange med meget mellem men mens mere mest mig min mine mit mod måske ned nej nemlig ni noget
nogen nogle nok nu når næste næsten og også om omkring op oppe os otte over overfor på samme sammen seks selv sidst sig
sin sine sit som stadig syv så sådan ti til tilbage tre to tusind ud ude uden udover under vi vor vores ved via ganske
netop snart straks ofte aldrig sjældent tit længe senere tidligere siden imens
""".split())
STOPWORDS = FUNCTION_WORDS | frozenset("""
år året årene uge ugen måned måneden tid tiden gang gange time timer minut dag dagen dage morgen aften nat weekend
land landet lande landene stat staten stater staterne krig krigen krige krigene regering regeringen regeringer
folk folket folkene magt magten magter magterne sag sagen sager sagerne by byen byer byerne verden verdens menneske
mennesker politik politikken parti partiet partier partierne minister ministeren ministre præsident præsidenten leder
lederen ledere lederne hær hæren hære militær militæret soldat soldater soldaterne våben våbnene fred freden aftale
aftalen aftaler aftalerne plan planen planer mål målet angreb angrebet angrebene konflikt konflikten konflikter
forhandling forhandlinger forhandlingerne valg valget vej vejen side del delen nyhed nyheder nyhederne historie
historien sted stedet steder hus huset arbejde arbejdet penge pengene økonomi økonomien olie olien gas gassen handel
handelen grænse grænsen grænser region regionen regioner område området områder hav havet havene ø øen øer kyst
kysten flod floden nord syd øst vest nordpå sydpå vesten østen union unionen kongerige kongeriget republik
republikken føderation føderationen styre styret styrer oprør oprøret oprører oprørere oprørerne milits militsen
militser bevægelse bevægelsen bevægelser gruppe gruppen grupper organisation organisationen myndighed myndigheden
myndigheder selvstyre selvstyret domstol domstolen råd rådet kommission kommissionen parlament parlamentet flåde
flåden base basen baser alliance alliancen pagt pagten front fronten lejr lejren golf grund grunden grunde
spørgsmål spørgsmålet svar svaret svarene læsning læsningen begreb begrebet ord ordet tekst teksten artikel avis
avisen medie medier medierne sprog sproget navn navnet liv livet død døden barn børn børnene mand manden mænd kvinde
kvinder familie familien skole skolen hospital hospitalet borger borgere borgerne befolkning befolkningen samfund
samfundet kultur kulturen religion religionen tro troen islam moské moskéen kirke kirken lov loven love regel
reglen regler ret retten rettigheder frihed friheden demokrati demokratiet valgkamp parlamentsvalg protest protester
protesten demonstration demonstrationer strejke krise krisen kriser inflation priser prisen pris skat skatten
told tolden marked markedet markeder virksomhed virksomheder bank banken banker energi energien strøm vand vandet
mad maden nødhjælp flygtning flygtninge flygtningene migrant migranter grænsekontrol politi politiet vagt sikkerhed
sikkerheden forsvar forsvaret trussel truslen trusler terror terrorisme drab drabet døde sårede fange fanger
gidsel gidsler våbenhvile våbenhvilen sanktion sanktioner sanktionerne topmøde topmødet møde mødet besøg besøget
tale talen udtalelse erklæring erklæringen beslutning beslutningen forslag forslaget krav kravet løfte løftet
rapport rapporten undersøgelse undersøgelsen tal tallet procent million millioner milliard milliarder kroner dollar
euro
er var være været har havde have haft bliver blev blive blevet kan kunne skal skulle vil ville må måtte får fik få
fået går gik gå gået kommer kom komme kommet siger sagde sige sagt ser se set giver gav give givet tager tog tage
taget gør gjorde gøre gjort står stod stå stået ligger lå ligge holder holdt holde bruger brugte bruge brugt mener
mente mene ment tror troede viser viste vise vist finder fandt finde fundet kalder kaldte kalde kaldt bor boede
lever levede leve dør dø dræber dræbte dræbe dræbt angriber angribe kæmper kæmpede kæmpe vinder vandt vinde
vundet taber tabte tabe tabt arbejder arbejdede betyder betød betyde handler handlede handle mødes mødtes mødte
fortsætter fortsatte fortsætte begynder begyndte begynde ender endte ende kræver krævede kræve støtter støttede
støtte presser pressede presse truer truede true frygter frygtede frygte ønsker ønskede ønske skriver skrev skrive
skrevet læser læste læse hører hørte høre spørger spurgte spørge svarer svarede svare sender sendte sende søger
søgte søge rejser rejste rejse åbner åbnede åbne lukker lukkede lukke stopper stoppede stoppe kører kørte køre
stor store større største lille små mindre mindst ny nye nyt nyeste gammel gamle ældre ældste god gode bedre bedst
dårlig dårlige værre lang lange længere kort korte høj høje højere lav lave ung unge mulig mulige umulig vigtig
vigtige vigtigste politisk politiske økonomisk økonomiske militære international internationale national nationale
regional regionale officiel officielle offentlig offentlige fælles fri frie åben svær svære let lette sikker sikre
klar klare rig rige fattig fattige stærk stærke svag svage hurtig hurtige nær nære fjern fjerne nuværende kommende
hel halv halve egentlig særlig særlige endelig endelige direkte indirekte fuld fulde tom tomme hård hårde blød
amerikansk amerikanske amerikaner amerikanere amerikanerne russisk russiske russer russere russerne kinesisk
kinesiske kineser kinesere kineserne britisk britiske brite briter briterne engelsk engelske englænder englændere
englænderne fransk franske franskmand franskmænd franskmændene tysk tyske tysker tyskere tyskerne israelsk israelske
israeler israelere israelerne jøde jøder jøderne jødisk jødiske iransk iranske iraner iranere iranerne persisk
persiske perser persere perserne arabisk arabiske araber arabere araberne saudisk saudiske saudier saudiere saudierne
saudiarabisk saudiarabiske tyrkisk tyrkiske tyrker tyrkere tyrkerne kurdisk kurdiske kurder kurdere kurderne
palæstinensisk palæstinensiske palæstinenser palæstinensere palæstinenserne syrisk syriske syrer syrere syrerne
libanesisk libanesiske libaneser libanesere libaneserne egyptisk egyptiske egypter egyptere egypterne irakisk
irakiske iraker irakere irakerne yemenitisk yemenitiske yemenit yemenitter yemenitterne ukrainsk ukrainske ukrainer
ukrainere ukrainerne dansk danske dansker danskere danskerne svensk svenske svensker svenskere svenskerne europæisk
europæiske europæer europæere europæerne vestlig vestlige østlig østlige vesterlænding vesterlændinge muslim muslimer
muslimerne muslimsk muslimske kristen kristne islamisk islamiske indisk indiske inder indere inderne pakistansk
pakistanske pakistaner pakistanere pakistanerne afghansk afghanske afghaner afghanere afghanerne sudanesisk
sudanesiske sudaneser sudanesere sudaneserne japansk japanske japaner japanere japanerne koreansk koreanske koreaner
koreanere qatarsk qatarske emiratisk emiratiske jordansk jordanske libysk libyske marokkansk marokkanske marokkaner
marokkanere algerisk algeriske tunesisk tunesiske etiopisk etiopiske somalisk somaliske somalier somaliere somalierne
nigeriansk nigerianske græsk græske græker grækere polsk polske polak polakker serbisk serbiske serber serbere armensk
armenske georgisk georgiske shiamuslim shiamuslimer shiamuslimerne sunnimuslim sunnimuslimer sunnimuslimerne shiitisk
shiitiske sunnitisk sunnitiske shia sunni vantro alawit alawitter alawitterne druser druserne uighur uighurer
uighurerne rohingya rohingyaer pashtun pashtunere beduin beduiner berber berbere tjetjener tjetjenere tatar tatarer
afrikaner afrikanere asiat asiater hindu hinduer hinduisk hinduistisk buddhist buddhister
""".split())
# a single-word alias ending like an adjective ('amerikansk', 'russiske', 'vestlige') is never a name
ADJECTIVE = re.compile(r'(?:isk|iske|sk|ske|lig|lige)$', re.I)
# the endings of the Danish words for peoples ('amerikaner', 'palæstinenserne', 'yemenitter', 'saudierne',
# 'franskmænd'); the stoplist holds the rest ('kurderne', 'jøderne', 'russerne')
PEOPLE = re.compile(r'(?:aner|anere|anerne|enser|ensere|enserne|itter|itterne|iere|ierne|mænd|mændene)$', re.I)
PEOPLE_OK = {'houthierne'}   # the movement Ansar Allah, as Danish news names it – not a people


def alias_problems(aliases_of, where_of=lambda k: k, clashes=True):
    """The alias rules over {page id: [aliases]}: a trimmed name, never an ordinary Danish word (the stoplist), an
    adjective or a word for a people, no banned voice, and (clashes) never an alias of two pages, in any case."""
    problems, seen = [], {}
    for k, aliases in aliases_of.items():
        for a in aliases:
            where = f'{where_of(k)} alias {a!r}'
            if not isinstance(a, str) or len(a.strip()) < 2 or a != ' '.join(a.split()):
                problems.append(f'{where}: an alias is a trimmed name of two or more characters')
                continue
            key = a.casefold()
            if clashes and key in seen and seen[key] != k:
                problems.append(f'{where}: also an alias of {seen[key]} – an alias names one page')
            seen.setdefault(key, k)
            words = key.split()
            if key in STOPWORDS or all(w in FUNCTION_WORDS for w in words):
                problems.append(f'{where}: an ordinary Danish word – a link names a state, power, group or issue')
            if len(words) == 1 and key not in PEOPLE_OK and (ADJECTIVE.search(key) or PEOPLE.search(key)):
                problems.append(f'{where}: reads as an adjective or a word for a people – a link names a state, power, '
                                'group or issue, never a people')
            bm.check_voice(a, where, problems)
    return problems


# ------------------------------------------------------------------------------------------------------ texts

ABBREV = re.compile(r'\b(?:bl\.a|f\.eks|m\.fl|m\.m|o\.l|osv|mia|mio|nr|ca|kl|jf|dvs|pga|inkl|evt|hhv|fx|St|gen|dr|prof)\.$',
                    re.I)
SPLIT = re.compile(r'(?:(?<=[.!?])|(?<=[.!?][»«")]))\s+(?=[A-ZÆØÅ»«"(])')
# the attribution a reading opens with, so two readings are compared on what they say
OPENING = re.compile(r'^Ifølge [^,:]{0,40}?Hizb ut-Tahrirs svar\w*(?: (?:af|fra|til og med) [\d/]+(?: til [\d/]+)?)?'
                     r'(?: \(\d+ svar\))?:?\s*')
KIND_ORDER = {'stilling': 0, 'rolle': 1, 'forhold': 2, 'tilstand': 3, 'plan': 4, 'fremgangsmåde': 5, 'motiv': 6}
RELATION_ORDER = {'forhold': 0, 'stilling': 1, 'rolle': 2, 'plan': 3, 'fremgangsmåde': 4, 'tilstand': 5, 'motiv': 6}
REPEAT = 0.5      # two readings of one answer this alike (words of four letters or more) are one reading


def sentences(text):
    out = []
    for part in SPLIT.split(' '.join(str(text or '').split())):
        if out and ABBREV.search(out[-1]):
            out[-1] += ' ' + part
        elif part:
            out.append(part)
    return out


def names_a_time(text):
    """A day, month or year ('12/6/2026', '27/9', 'marts 2015', '2013-2015')."""
    return bool(bm.dates_in(text) or re.search(r'\b\d{1,2}/\d{1,2}\b', text or ''))


def newest_first(nrs, answers):
    nrs = [n for n in dict.fromkeys(nrs) if n in answers]
    return sorted(nrs, key=lambda n: (answers[n]['date'], n), reverse=True)


# --------------------------------------------------------------------------------------------------- the build

def load(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def seed_names(seed):
    names, parents = {}, {}
    for group in ('states', 'actors', 'powers'):    # the later group wins: the powers' and actors' plain names
        for k, v in (seed.get(group) or {}).items():
            if v.get('name'):
                names[k] = v['name']
    for k, v in (seed.get('issues') or {}).items():
        if v.get('parent'):
            parents[k] = v['parent']
    return names, set(seed.get('powers') or {}), parents


def with_date(text, first, last=None):
    """A reading that names the movement but no day gets its answers' span in the attribution ('Ifølge Hizb ut-Tahrirs
    svar fra 12/3/2016 til 29/7/2018 samlede …'), so a timeline row read alone says when."""
    if names_a_time(text):
        return text
    span = f'fra {bm.d_slash(first)} til {bm.d_slash(last)}' if last and last != first else f'af {bm.d_slash(first)}'
    m = re.search(r'Hizb ut-Tahrirs svar(?:ene)?(?=[ ,:])', text)
    if not m:
        return f'Ifølge Hizb ut-Tahrirs svar {span}: {text}'
    return f'{text[:m.end()]} {span}{text[m.end():]}'


def timeline_of(rows):
    """The readings newest first (a standing before the rest of one answer), a repeat of one answer's reading once,
    each naming its day."""
    order = sorted(range(len(rows)), key=lambda i: (KIND_ORDER.get(rows[i]['kind'], 9), i))
    order.sort(key=lambda i: rows[i]['date'], reverse=True)
    out = []
    for i in order:
        r = rows[i]
        core = OPENING.sub('', r['text_da'])
        dup = next((x for x in out if x['nr'] == r['nr'] and bm.similar(x['_core'], core) >= REPEAT), None)
        if dup is None:
            out.append({'date': r['date'], 'nr': r['nr'], 'text_da': r['text_da'], '_core': core, '_last': r.get('last')})
        elif len(r['text_da']) > len(dup['text_da']):
            dup.update(text_da=r['text_da'], _core=core, _last=r.get('last'))
    return [{'date': x['date'], 'nr': x['nr'], 'text_da': with_date(x['text_da'], x['date'], x['_last'])} for x in out]


def reading_rows_nrs(rows):
    out = []
    for r in rows:
        out += [r['nr']] + list(r.get('also') or []) + ([r['last_nr']] if r.get('last_nr') else [])
    return out


def build(now=None, ideas=None):
    """(document, report): the wiki and what the build noticed (clashes, concepts left out). ideas: the concept
    file's content, or None to read docs/hjerne/begreber-ideer.json when it is there."""
    layer = load(LAYER)
    index = load(MINDEX)
    seed = load(SEED)
    if layer is None or index is None:
        raise SystemExit('public/viden/movement.json and movement-index.json are needed: run py scripts/build_movement.py')
    if seed is None:
        raise SystemExit('docs/hjerne/knowledge-v0.json is needed for the names of the states, powers and actors')
    answers = index['answers']
    names, powers, parents = seed_names(seed)
    readings, current, issues = layer['readings'], layer['current'], layer['issues']
    report = []

    # ---- the states, powers and groups
    subjects = sorted({s for s in set(readings) | set(current) if '--' not in s})
    relations = sorted({s for s in set(readings) | set(current) if '--' in s})
    parties = sorted({p for r in relations for p in r.split('--')} - set(subjects))
    items = {}
    for sid in subjects + parties:
        name = NAMES.get(sid) or names.get(sid) or EXTRA_NAMES.get(sid)
        if not name:
            raise SystemExit(f'{sid}: no name – add it to EXTRA_NAMES')
        if sid not in ALIASES:
            raise SystemExit(f'{sid}: no Danish forms – add them to ALIASES')
        kind = KIND.get(sid) or ('magt' if sid in powers else 'stat')
        e = {'id': sid, 'name': name, 'kind': kind, 'aliases': list(ALIASES[sid]),
             'case_sensitive': sid not in CASE_INSENSITIVE, 'timeline': timeline_of(readings.get(sid) or []),
             'relations': [], 'answers': [], 'related': []}
        c = current.get(sid)
        if c:
            e.update(lead_da=c['text_da'], lead_nr=c['nr'], lead_date=c['date'])
        elif e['timeline']:
            top = e['timeline'][0]
            e.update(lead_da=top['text_da'], lead_nr=top['nr'], lead_date=top['date'])
        if sid in readings or sid in current:
            e['subject'] = sid
        e['_nrs'] = reading_rows_nrs(readings.get(sid) or []) + ([c['nr']] + ([c['latest_nr']] if c.get('latest_nr') else [])
                                                                  if c else [])
        items[sid] = e

    # ---- relations on both parties' pages
    for rid in relations:
        a, b = rid.split('--')
        c = current.get(rid)
        rows = readings.get(rid) or []
        if c:
            rel = {'text_da': c['text_da'], 'date': c['date'], 'nr': c['nr']}
        else:
            newest = max(r['date'] for r in rows)
            r = min((r for r in rows if r['date'] == newest), key=lambda r: (RELATION_ORDER.get(r['kind'], 9), -len(r['text_da'])))
            rel = {'text_da': r['text_da'], 'date': r['date'], 'nr': r['nr']}
        nrs = reading_rows_nrs(rows) + ([c['nr']] + ([c['latest_nr']] if c.get('latest_nr') else []) if c else [])
        for me, other in ((a, b), (b, a)):
            items[me]['relations'].append({'with': other, **rel})
            items[me]['_nrs'] += nrs
    for e in items.values():
        e['relations'].sort(key=lambda r: (r['date'], r['with']), reverse=True)
        if 'lead_da' not in e and e['relations']:       # a party only a relation names: that relation leads
            r = e['relations'][0]
            e.update(lead_da=r['text_da'], lead_nr=r['nr'], lead_date=r['date'])

    # ---- answers: tagged in the index, or behind a reading or relation
    tagged = {}
    for nr, a in answers.items():
        for s in set(a.get('states') or []) | set(a.get('powers') or []):
            tagged.setdefault(('s', s), []).append(nr)
        for s in a.get('issues') or []:
            tagged.setdefault(('i', s), []).append(nr)
    for sid, e in items.items():
        e['answers'] = newest_first(tagged.get(('s', sid), []) + e.pop('_nrs'), answers)
    for src, nr, word, pages in SHARED_READINGS:
        row = max((r for r in readings.get(src) or [] if r['nr'] == nr and word in r['text_da']),
                  key=lambda r: len(r['text_da']), default=None)
        for k in pages if row else ():
            e = items.get(k)
            if e and nr not in {r['nr'] for r in e['timeline']}:
                e['timeline'] = sorted(e['timeline'] + [{'date': row['date'], 'nr': nr, 'text_da': row['text_da']}],
                                       key=lambda r: r['date'], reverse=True)
                e['answers'] = newest_first(e['answers'] + [nr], answers)
    for e in items.values():
        newest_lead(e, answers)

    # ---- the issues
    sag_id = {iid: (f'{iid}-sagen' if iid in items else iid) for iid in issues}
    for iid, v in issues.items():
        pid = sag_id[iid]
        if iid in items:
            name = f"{items[iid]['name']}-sagen"
        else:
            name = ISSUE_NAMES.get(iid) or (seed.get('issues') or {}).get(iid, {}).get('name')
        if not name:
            raise SystemExit(f'issue {iid}: no name – add it to ISSUE_NAMES')
        own = [n for n in dict.fromkeys(v['nrs']) if n in answers]
        unknown = [n for n in v['nrs'] if n not in answers]
        if unknown:
            report.append(f'issue {iid}: answers not in movement-index.json left out: {unknown}')
        parts = sentences(v['history_da'])
        if iid in SAG_LEAD:
            lead = SAG_LEAD[iid]
        elif iid in LEAD_PICK:
            lead = ' '.join(parts[i] for i in LEAD_PICK[iid])
        else:
            lead = ' '.join(parts if len(parts) <= LEAD_SENTENCES else [parts[0]] + parts[-(LEAD_SENTENCES - 1):])
        everything = newest_first(own + tagged.get(('i', iid), []), answers)
        if not everything:
            raise SystemExit(f'issue {iid}: no answer in movement-index.json')
        # the lead's governing answer: the newest its first sentence cites by its day (its own answers first), else
        # the newest the lead cites, else its newest
        first = (sentences(lead) or [lead])[0]
        lead_nr = next((n for n in newest_first(own, answers) + everything if cited(first, answers[n]['date'])),
                       next((n for n in newest_first(own, answers) + everything if cited(lead, answers[n]['date'])),
                            (newest_first(own, answers) or everything)[0]))
        items[pid] = {'id': pid, 'name': name, 'kind': 'sag', 'aliases': list(ISSUE_ALIASES.get(iid) or []),
                      'case_sensitive': iid not in ISSUE_CASE_INSENSITIVE, 'lead_da': lead, 'lead_nr': lead_nr,
                      'lead_date': answers[lead_nr]['date'],
                      'timeline': [{'date': answers[n]['date'], 'nr': n, 'text_da': layer['answers'][n]['note_da']}
                                   for n in newest_first(own, answers) if n not in ROW_EXCLUDE.get(iid, ())],
                      'relations': [], 'answers': everything, 'related': [], 'subject': iid, '_own': own,
                      'history_da': v['history_da']}

    # ---- related. An issue links the pages it is named after ('afghanistan-pakistan': Afghanistan, Pakistan; 'iran':
    # Iran), the states, powers, groups and issues its history names, and the groups and organisations whose readings
    # rest on its answers (histories seldom name them), the most central first (the share of the issue's answers
    # tagged with the page); then the issue above it and those below. A state, power or group links its own issues,
    # its relations' other parties (newest first), then the issues that link it (most shared answers first); a page no
    # issue links gets the one or two issues its answers are tagged with most (Belarus: Ukraine og Rusland).
    pattern = {k: name_pattern(e) for k, e in items.items()}
    reads = {k: {r['nr'] for r in e['timeline']} | {e['lead_nr']} for k, e in items.items() if e['kind'] != 'sag'}

    def share(k, pool):
        e = items[k]
        tag = (lambda a: e['subject'] in (a.get('issues') or [])) if e['kind'] == 'sag' else \
            (lambda a: k in set(a.get('states') or []) | set(a.get('powers') or []))
        return sum(1 for n in pool if tag(answers[n])) / max(1, len(pool))

    def named_after(iid, k):
        return iid == k or iid.startswith(k + '-') or iid.endswith('-' + k) or f'-{k}-' in iid

    for iid in issues:
        pid = sag_id[iid]
        s = items[pid]
        found = {}
        for k, rx in pattern.items():
            m = rx.search(issues[iid]['history_da']) if rx is not None and k != pid else None
            if m:
                found[k] = m.start()
        for k in reads:
            if named_after(iid, k):
                found[k] = -1
            elif items[k]['kind'] in ('gruppe', 'organisation') and reads[k] & set(s['_own']):
                found.setdefault(k, 10 ** 6)
        s['related'] = sorted(found, key=lambda k: (found[k] != -1, -share(k, s['answers']), found[k]))
        family = [parents.get(iid)] + sorted(k for k, p in parents.items() if p == iid)   # the issue above, those below
        s['related'] += [sag_id[k] for k in family if k in sag_id and sag_id[k] not in s['related']]

    def tagged_most(sid):
        score = {}
        for n in items[sid]['answers']:
            tags = [t for t in answers[n].get('issues') or [] if t in sag_id]
            for j, t in enumerate(tags):
                score[t] = score.get(t, 0) + (1.5 if j == 0 else 1)     # an answer's first issue is its main one
        best = sorted(score, key=lambda t: (-score[t], t))[:2]
        return [sag_id[t] for t in best if score[t] >= max(score.values()) - 0.5] if score else []

    for sid in reads:
        e = items[sid]
        partners = [r['with'] for r in e['relations']]
        own = [sag_id[i] for i in issues if named_after(i, sid)]
        linking = [sag_id[i] for i in issues if sid in items[sag_id[i]]['related'] and sag_id[i] not in own]
        linking.sort(key=lambda p: (-len(reads[sid] & set(items[p]['_own'])), -share(sid, items[p]['answers']), p))
        e['related'] = list(dict.fromkeys(own + partners + (linking if own or linking else tagged_most(sid))))
    for e in items.values():
        e.pop('_own', None)

    # ---- the concepts, when their file is there (a file another part of the work may be writing right now)
    if ideas is None:
        try:
            ideas = load(IDEAS)
        except ValueError as err:
            report.append(f'begreber-ideer.json is not valid JSON ({err}) – the concepts are left out')
            ideas = None
    if ideas:
        merge_ideas(items, ideas, answers, report)

    for e in items.values():
        e['related'] = [k for k in dict.fromkeys(e['related']) if k in items and k != e['id']]
    doc = {'version': 1, 'built': (now or datetime.now(timezone.utc)).isoformat(timespec='seconds'),
           'items': {k: ordered(items[k]) for k in sorted(items)}}
    return doc, report


def drop_cited(text, iso):
    """The lead without what it says of one answer's day (that answer now leads): a clause ('…; svaret af 27/9/2026
    ser …', '…, og svaret af 1/5/2026 nævner …') or a sentence that opens on it."""
    y, m, d = iso.split('-')
    day = rf'{int(d)}/{int(m)}(?:/{y})?(?![\d/])'
    out = []
    for sent in sentences(text):
        if re.match(rf'^(?:Ifølge )?(?:Hizb ut-Tahrirs )?[Ss]vare[tn] (?:af )?{day}', sent):
            continue
        sent = re.sub(rf'(?:,? og|;) (?:ifølge )?svaret (?:af )?{day}[^.;]*', '', sent)
        out.append(sent if sent.endswith(('.', '!', '?')) else sent + '.')
    return ' '.join(out)


def newest_lead(e, answers):
    """The newest answer governs the first sentence. A state's, group's or organisation's newer reading than its current
    one leads, the current reading after it (without what it said of that answer); a lead whose attribution names no
    day ('Ifølge Hizb ut-Tahrirs svar 2023-2025 …') rests on the newest answer its first sentence cites."""
    if not e.get('lead_da'):
        return
    row = e['timeline'][0] if e['timeline'] else None
    if row and row['date'] > e['lead_date'] and e['kind'] not in LEAD_IS_STANDING:
        rest = sentences(drop_cited(e['lead_da'], row['date']))
        lead = [row['text_da']] + rest
        while len(lead) > LEAD_SENTENCES:
            lead.pop()
        e.update(lead_da=' '.join(lead), lead_nr=row['nr'], lead_date=row['date'])
    if not re.match(r'^Ifølge Hizb ut-Tahrirs svar af \d', e['lead_da']):
        first = (sentences(e['lead_da']) or [''])[0]
        hit = next((n for n in e['answers'] if n in answers and cited(first, answers[n]['date'])), None)
        if hit and answers[hit]['date'] > e['lead_date']:
            e.update(lead_nr=hit, lead_date=answers[hit]['date'])


def cited(text, iso):
    """Whether a text names this day ('28/6/2026', or '28/6' without the year)."""
    y, m, d = iso.split('-')
    return bool(re.search(rf'(?<![\d/]){int(d)}/{int(m)}(?:/{y})?(?![\d/])', text or ''))


def name_pattern(e):
    """A page's names as one pattern: a whole word, with a possessive s ('Irans', "USA's")."""
    names = [a for a in e['aliases'] if a] + ([] if e['kind'] == 'sag' else [re.sub(r'\s*\(.*\)$', '', e['name'])])
    names = sorted({n for n in names if len(n) >= 2}, key=len, reverse=True)
    if not names:
        return None
    return re.compile(r"(?<![\w-])(?:" + '|'.join(map(re.escape, names)) + r")(?:s|'s|’s|')?(?!\w)",
                      0 if e['case_sensitive'] else re.I)


def ordered(e):
    out = {f: e[f] for f in FIELDS if f in e}
    out.update({k: v for k, v in e.items() if k not in out})
    return out


def merge_ideas(items, ideas, answers, report):
    """The concept pages join the wiki. A concept that breaks the schema or a voice rule is left out; an answer number
    or a relation the wiki does not know is dropped, and so is an alias that breaks the alias rules. The concept's own
    entry wins an id clash, its alias wins an alias clash (the movement page loses the alias), each reported; a page
    a concept names as related links back to it."""
    got = ideas.get('items') if isinstance(ideas, dict) else None
    if not isinstance(got, dict):
        report.append("begreber-ideer.json: no 'items' object – the concepts are left out")
        return
    names = bm.protected_names()
    kept = {}
    for cid, c in sorted(got.items()):
        if not isinstance(c, dict):
            report.append(f'concept {cid}: not an object – left out')
            continue
        c = dict(c)
        c.setdefault('id', cid)
        c.setdefault('case_sensitive', True)
        for f in ('aliases', 'timeline', 'relations', 'answers', 'related'):
            c[f] = list(c.get(f) or [])
        c['answers'] = [str(n) for n in c['answers']]
        bad = [n for n in c['answers'] if n not in answers]
        if bad:
            report.append(f'concept {cid}: answers not in movement-index.json dropped: {bad}')
        c['answers'] = newest_first(c['answers'], answers)
        gone = [r for r in c['relations'] if not isinstance(r, dict) or r.get('with') not in items]
        if gone:
            report.append(f"concept {cid}: relations with no page dropped: {[r.get('with') for r in gone if isinstance(r, dict)]}")
            c['relations'] = [r for r in c['relations'] if r not in gone]
        problems = entry_problems(c, answers, f'concept {cid}')
        if c.get('id') != cid:
            problems.append(f"concept {cid}: id {c.get('id')!r} differs from its key")
        if not problems:
            for where, t in page_texts(cid, c):
                problems += text_problems(f'concept {where}', t, names)
        if problems:
            report += [f'{p} – the concept is left out' for p in problems]
            continue
        rules = alias_problems({cid: c['aliases']}, lambda k: f'concept {k}', clashes=False)
        if rules:
            report += [f'{p} – the alias is dropped' for p in rules]
            c['aliases'] = [a for a in c['aliases'] if not any(f'alias {a!r}:' in p for p in rules)]
        if c.get('case_sensitive') and any(a[:1].islower() for a in c['aliases']):
            report.append(f'concept {cid}: a lower-case alias on a case-sensitive page – the page is made case-insensitive')
            c['case_sensitive'] = False
        if cid in items:
            report.append(f"id clash: the concept '{cid}' replaces the movement's {items[cid]['kind']} page of that id")
        kept[cid] = c
    owner = {}
    for cid, c in kept.items():
        mine = []
        for a in c['aliases']:
            key = a.casefold()
            if key in owner:
                report.append(f"alias clash: '{a}' is an alias of the concepts {owner[key]} and {cid} – kept on {owner[key]}")
                continue
            owner[key] = cid
            mine.append(a)
        c['aliases'] = mine
    items.update(kept)
    for k, e in items.items():
        if k in kept:
            continue
        lost = [a for a in e['aliases'] if a.casefold() in owner]
        for a in lost:
            report.append(f"alias clash: '{a}' of the page {k} is the concept {owner[a.casefold()]}'s – kept on the concept")
        e['aliases'] = [a for a in e['aliases'] if a not in lost]
    for cid, c in kept.items():
        for k in c['related']:
            if k not in items:
                report.append(f'concept {cid}: related {k!r} is no page – dropped')
            elif k not in kept and cid not in items[k]['related']:
                items[k]['related'].append(cid)


# --------------------------------------------------------------------------------------------------- the check

def entry_problems(e, answers, where):
    """One page against the schema: its fields and types, attributed and dated texts, known answers with their own
    dates, newest first, the lead at most four sentences."""
    problems = []
    for f in ('id', 'name', 'kind', 'lead_da', 'lead_nr', 'lead_date'):
        if not isinstance(e.get(f), str) or not e.get(f).strip():
            problems.append(f'{where}: {f} must be a non-empty text')
    if problems:
        return problems
    if not ID.match(e['id']):
        problems.append(f"{where}: the id {e['id']!r} is not lower-case a-z, 0-9 and '-'")
    if e['kind'] not in KINDS:
        problems.append(f"{where}: kind {e['kind']!r} is not one of {', '.join(KINDS)}")
    if not isinstance(e.get('case_sensitive'), bool):
        problems.append(f'{where}: case_sensitive must be true or false')
    for f in ('aliases', 'timeline', 'relations', 'answers', 'related'):
        if not isinstance(e.get(f), list):
            problems.append(f'{where}: {f} must be a list')
    if e.get('subject') is not None and not isinstance(e['subject'], str):
        problems.append(f'{where}: subject must be a text')
    if problems:
        return problems

    def dated(w, nr, when):
        if nr not in answers:
            problems.append(f'{w}: unknown answer {nr!r} (not in movement-index.json)')
        elif when != answers[nr]['date']:
            problems.append(f"{w}: dated {when}, but answer {nr} is of {answers[nr]['date']}")

    def text(w, t):
        if not isinstance(t, str) or not t.strip():
            problems.append(f'{w}: no text')
            return
        if 'Hizb ut-Tahrir' not in t:
            problems.append(f"{w}: not attributed – the movement's reading names it ('Ifølge Hizb ut-Tahrirs svar af …'): {t[:80]}")
        if not names_a_time(t):
            problems.append(f'{w}: names no date: {t[:80]}')
    text(f'{where} lead', e['lead_da'])
    dated(f'{where} lead', e['lead_nr'], e['lead_date'])
    n = len(sentences(e['lead_da']))
    if n > LEAD_SENTENCES:
        problems.append(f'{where} lead: {n} sentences – at most {LEAD_SENTENCES}')
    first = (sentences(e['lead_da']) or [''])[0]
    if not cited(first, e['lead_date']):
        problems.append(f"{where} lead: the first sentence must name its answer's day ({bm.d_slash(e['lead_date'])}) – "
                        'the newest answer leads')
    newer = [r for r in e['timeline'] if isinstance(r, dict) and str(r.get('date')) > e['lead_date']]
    if newer and e['kind'] not in LEAD_IS_STANDING | {'sag'}:
        problems.append(f"{where} lead: the timeline has a newer reading ({newer[0]['date']}, nr {newer[0]['nr']}) than "
                        f"the lead ({e['lead_date']}) – the newest answer leads")
    if e['kind'] == 'sag':
        main = [r for r in newer if (answers.get(r['nr']) or {}).get('issues', [None])[:1] == [e.get('subject')]]
        if main:
            problems.append(f"{where} lead: the issue's newest main answer ({main[0]['date']}, nr {main[0]['nr']}) is "
                            f"newer than the lead ({e['lead_date']}) – write a new lead in scripts/begreber_leads.py")
    last = None
    for i, r in enumerate(e['timeline']):
        w = f'{where} timeline[{i}]'
        if not isinstance(r, dict) or set(r) != {'date', 'nr', 'text_da'}:
            problems.append(f'{w}: a row is {{date, nr, text_da}}')
            continue
        text(w, r['text_da'])
        dated(w, r['nr'], r['date'])
        if last and r['date'] > last:
            problems.append(f'{w}: not newest first')
        last = r['date']
    for i, r in enumerate(e['relations']):
        w = f'{where} relation[{i}]'
        if not isinstance(r, dict) or set(r) != {'with', 'text_da', 'date', 'nr'}:
            problems.append(f'{w}: a row is {{with, text_da, date, nr}}')
            continue
        text(w, r['text_da'])
        dated(w, r['nr'], r['date'])
    if len(set(e['answers'])) != len(e['answers']):
        problems.append(f'{where}: an answer listed twice')
    for nr in e['answers']:
        if nr not in answers:
            problems.append(f'{where} answers: unknown answer {nr!r}')
    known = [nr for nr in e['answers'] if nr in answers]
    if known != newest_first(known, answers):
        problems.append(f'{where} answers: not newest first')
    return problems


def page_texts(k, e):
    yield f'{k} name', e.get('name') or ''
    yield f'{k} lead', e.get('lead_da') or ''
    for i, r in enumerate(e.get('timeline') or []):
        yield f'{k} timeline[{i}]', (r.get('text_da') if isinstance(r, dict) else '') or ''
    for i, r in enumerate(e.get('relations') or []):
        yield f'{k} relation[{i}]', (r.get('text_da') if isinstance(r, dict) else '') or ''


def text_problems(where, t, names):
    """The movement layer's voice (build_movement.check) on one text: no forgeries or verdicts on peoples, Israel by its
    name, no agent words, no attack said to be staged, no serving claim about a protected or non-ruling person or a
    party, no long quotations, no local paths."""
    problems = []
    bm.check_voice(t, where, problems)
    hit = re.search(r'\bagent\w*', t, re.I)
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' – the layer says 'underordnet' (H1)")
    if bm.LOCAL.search(t):
        problems.append(f'{where}: a local path or private name')
    for q in (a or b for a, b in bm.QUOTE.findall(t)):
        if len(q) > bm.QUOTE_MAX:
            problems.append(f'{where}: a quotation over {bm.QUOTE_MAX} characters')
    bm.serving_problems(where, t, names, problems)
    return problems


def check(doc, answers=None):
    """Every page keeps the schema and Khabar's rules: attributed, dated texts whose answers exist; aliases that name
    one page and are never an ordinary word, an adjective or a word for a people; related ids and relations that are
    pages; and the voice of the movement layer in every text."""
    answers = answers if answers is not None else load(MINDEX)['answers']
    items = doc.get('items') if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or doc.get('version') != 1 or not isinstance(items, dict):
        return ['begreber.json: version 1 with an items object']
    problems = []
    names = bm.protected_names()
    for k, e in items.items():
        own = entry_problems(e, answers, k)
        problems += own
        if own:
            continue
        if e['id'] != k:
            problems.append(f"{k}: id {e['id']!r} differs from its key")
        for r in e['related']:
            if r not in items or r == k:
                problems.append(f'{k}: related {r!r} is no other page')
        for r in e['relations']:
            if r['with'] not in items or r['with'] == k:
                problems.append(f"{k}: relation with {r['with']!r}, which is no other page")
        if e['case_sensitive'] and any(isinstance(a, str) and a[:1].islower() for a in e['aliases']):
            problems.append(f'{k}: a lower-case alias on a case-sensitive page – make the page case-insensitive')
        for where, t in page_texts(k, e):
            problems += text_problems(where, t, names)
    problems += alias_problems({k: e.get('aliases') or [] for k, e in items.items() if isinstance(e, dict)})
    return problems


def index_of(doc):
    """The app's linker index: per page its name, kind, aliases, case and how many answers it holds."""
    return {'version': 1, 'items': {k: {'name': e['name'], 'kind': e['kind'], 'aliases': e['aliases'],
                                        'case_sensitive': e['case_sensitive'], 'n_answers': len(e['answers'])}
                                    for k, e in doc['items'].items()}}


def main():
    doc, report = build()
    for line in report:
        print(' ·', line)
    problems = check(doc)
    for p in problems:
        print(' -', p)
    if problems:
        sys.exit(1)
    text = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
    slim = json.dumps(index_of(doc), ensure_ascii=False, separators=(',', ':'))
    OUT.write_text(text, encoding='utf-8')
    OUT_INDEX.write_text(slim, encoding='utf-8')
    items = doc['items']
    kinds = {}
    for e in items.values():
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print(f"pages {len(items)} ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))}) · "
          f"aliases {sum(len(e['aliases']) for e in items.values())} · timeline rows "
          f"{sum(len(e['timeline']) for e in items.values())} · relations {sum(len(e['relations']) for e in items.values())} · "
          f"{len(text.encode('utf-8'))} bytes (index {len(slim.encode('utf-8'))} bytes)")
    print('most answers:', ', '.join(f"{e['name']} {len(e['answers'])}" for e in
                                     sorted(items.values(), key=lambda e: (-len(e['answers']), e['id']))[:10]))


if __name__ == '__main__':
    main()
